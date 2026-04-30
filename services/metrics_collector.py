"""
Application Metrics Collector Service
Tracks RPS, response times, error rates, and other application performance metrics.
Uses in-memory storage with time-based expiration for lightweight operation.
"""

import time
import threading
from collections import deque
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


@dataclass
class RequestMetric:
    """Single request metric data point."""
    timestamp: float
    path: str
    method: str
    status_code: int
    response_time_ms: float
    is_error: bool = False


@dataclass
class MetricsSummary:
    """Aggregated metrics summary."""
    requests_per_second: float = 0.0
    total_requests: int = 0
    error_count_4xx: int = 0
    error_count_5xx: int = 0
    error_rate: float = 0.0
    avg_response_time_ms: float = 0.0
    p95_response_time_ms: float = 0.0
    p99_response_time_ms: float = 0.0
    min_response_time_ms: float = 0.0
    max_response_time_ms: float = 0.0
    failed_requests_1h: int = 0


class MetricsCollector:
    """
    Thread-safe metrics collector for application performance monitoring.
    Stores metrics in memory with automatic cleanup of old data.
    """
    
    # Configuration thresholds
    THRESHOLDS = {
        'cpu_warning': 70,
        'cpu_critical': 90,
        'memory_warning': 80,
        'memory_critical': 95,
        'disk_warning': 80,
        'disk_critical': 95,
        'error_rate_warning': 1.0,  # 1%
        'error_rate_critical': 5.0,  # 5%
        'response_time_warning': 500,  # ms
        'response_time_critical': 2000,  # ms
        'db_connections_warning': 80,  # % of max
        'db_connections_critical': 95,
        'db_latency_warning': 100,  # ms
        'db_latency_critical': 500,
    }
    
    # Retention periods
    RETENTION_DETAILED = 3600  # 1 hour for detailed metrics
    RETENTION_AGGREGATED = 1800  # 30 minutes for sparkline data
    AGGREGATION_INTERVAL = 60  # 1 minute buckets for sparklines
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern for global metrics access."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self._metrics_lock = threading.Lock()
        
        # Detailed request metrics (last 1 hour)
        self._request_metrics: deque = deque(maxlen=100000)
        
        # Aggregated metrics for sparklines (last 30 minutes, 1-minute buckets)
        self._cpu_history: deque = deque(maxlen=30)
        self._memory_history: deque = deque(maxlen=30)
        self._rps_history: deque = deque(maxlen=30)
        self._error_rate_history: deque = deque(maxlen=30)
        self._response_time_history: deque = deque(maxlen=30)
        
        # Database metrics
        self._db_latency_history: deque = deque(maxlen=30)
        self._slow_query_count = 0
        self._db_error_count = 0
        
        # Application state
        self._app_start_time = time.time()
        self._last_aggregation_time = time.time()
        
        # Start background cleanup thread
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()
        
        logger.info("MetricsCollector initialized")
    
    def record_request(self, path: str, method: str, status_code: int, response_time_ms: float):
        """Record a single HTTP request metric."""
        metric = RequestMetric(
            timestamp=time.time(),
            path=path,
            method=method,
            status_code=status_code,
            response_time_ms=response_time_ms,
            is_error=status_code >= 400
        )
        
        with self._metrics_lock:
            self._request_metrics.append(metric)
    
    def record_db_latency(self, latency_ms: float, is_slow: bool = False, is_error: bool = False):
        """Record database operation latency."""
        with self._metrics_lock:
            if is_slow:
                self._slow_query_count += 1
            if is_error:
                self._db_error_count += 1
    
    def record_system_metrics(self, cpu_percent: float, memory_percent: float):
        """Record system resource metrics for sparklines."""
        current_time = time.time()
        
        with self._metrics_lock:
            # Only record if enough time has passed since last aggregation
            if current_time - self._last_aggregation_time >= self.AGGREGATION_INTERVAL:
                self._cpu_history.append({
                    'timestamp': current_time,
                    'value': cpu_percent
                })
                self._memory_history.append({
                    'timestamp': current_time,
                    'value': memory_percent
                })
                
                # Calculate and record RPS and error rate
                summary = self._calculate_summary_internal(60)  # Last minute
                self._rps_history.append({
                    'timestamp': current_time,
                    'value': summary.requests_per_second
                })
                self._error_rate_history.append({
                    'timestamp': current_time,
                    'value': summary.error_rate
                })
                self._response_time_history.append({
                    'timestamp': current_time,
                    'value': summary.avg_response_time_ms
                })
                
                self._last_aggregation_time = current_time
    
    def get_summary(self, window_seconds: int = 60) -> MetricsSummary:
        """Get aggregated metrics summary for the specified time window."""
        with self._metrics_lock:
            return self._calculate_summary_internal(window_seconds)
    
    def _calculate_summary_internal(self, window_seconds: int) -> MetricsSummary:
        """Internal method to calculate summary (must be called with lock held)."""
        cutoff_time = time.time() - window_seconds
        
        # Filter recent metrics
        recent_metrics = [m for m in self._request_metrics if m.timestamp >= cutoff_time]
        
        if not recent_metrics:
            return MetricsSummary()
        
        total = len(recent_metrics)
        errors_4xx = sum(1 for m in recent_metrics if 400 <= m.status_code < 500)
        errors_5xx = sum(1 for m in recent_metrics if m.status_code >= 500)
        
        response_times = sorted([m.response_time_ms for m in recent_metrics])
        
        # Calculate percentiles
        p95_idx = int(len(response_times) * 0.95)
        p99_idx = int(len(response_times) * 0.99)
        
        return MetricsSummary(
            requests_per_second=total / window_seconds if window_seconds > 0 else 0,
            total_requests=total,
            error_count_4xx=errors_4xx,
            error_count_5xx=errors_5xx,
            error_rate=(errors_4xx + errors_5xx) / total * 100 if total > 0 else 0,
            avg_response_time_ms=sum(response_times) / len(response_times),
            p95_response_time_ms=response_times[p95_idx] if p95_idx < len(response_times) else 0,
            p99_response_time_ms=response_times[p99_idx] if p99_idx < len(response_times) else 0,
            min_response_time_ms=min(response_times),
            max_response_time_ms=max(response_times),
            failed_requests_1h=self._count_failed_requests_1h()
        )
    
    def _count_failed_requests_1h(self) -> int:
        """Count failed requests in the last hour."""
        cutoff_time = time.time() - 3600
        return sum(1 for m in self._request_metrics if m.timestamp >= cutoff_time and m.is_error)
    
    def get_sparkline_data(self) -> Dict:
        """Get historical data for sparkline charts."""
        with self._metrics_lock:
            return {
                'cpu': list(self._cpu_history),
                'memory': list(self._memory_history),
                'rps': list(self._rps_history),
                'error_rate': list(self._error_rate_history),
                'response_time': list(self._response_time_history)
            }
    
    def get_db_metrics(self) -> Dict:
        """Get database-related metrics."""
        with self._metrics_lock:
            return {
                'slow_query_count': self._slow_query_count,
                'error_count': self._db_error_count,
                'latency_history': list(self._db_latency_history)
            }
    
    def get_app_uptime(self) -> Dict:
        """Get application uptime information."""
        uptime_seconds = time.time() - self._app_start_time
        days, remainder = divmod(int(uptime_seconds), 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        return {
            'started_at': datetime.fromtimestamp(self._app_start_time).isoformat(),
            'uptime_seconds': uptime_seconds,
            'uptime_formatted': f"{days}d {hours}h {minutes}m {seconds}s",
            'days': days,
            'hours': hours,
            'minutes': minutes,
            'seconds': seconds
        }
    
    def get_health_status(self, metrics: Dict) -> str:
        """Determine overall health status based on metrics and thresholds."""
        # Check critical conditions
        if metrics.get('cpu_percent', 0) >= self.THRESHOLDS['cpu_critical']:
            return 'critical'
        if metrics.get('memory_percent', 0) >= self.THRESHOLDS['memory_critical']:
            return 'critical'
        if metrics.get('disk_percent', 0) >= self.THRESHOLDS['disk_critical']:
            return 'critical'
        if metrics.get('error_rate', 0) >= self.THRESHOLDS['error_rate_critical']:
            return 'critical'
        if metrics.get('db_connection_percent', 0) >= self.THRESHOLDS['db_connections_critical']:
            return 'critical'
        
        # Check warning conditions
        if metrics.get('cpu_percent', 0) >= self.THRESHOLDS['cpu_warning']:
            return 'warning'
        if metrics.get('memory_percent', 0) >= self.THRESHOLDS['memory_warning']:
            return 'warning'
        if metrics.get('disk_percent', 0) >= self.THRESHOLDS['disk_warning']:
            return 'warning'
        if metrics.get('error_rate', 0) >= self.THRESHOLDS['error_rate_warning']:
            return 'warning'
        if metrics.get('db_connection_percent', 0) >= self.THRESHOLDS['db_connections_warning']:
            return 'warning'
        
        return 'healthy'
    
    def _cleanup_loop(self):
        """Background thread to clean up old metrics."""
        while True:
            try:
                time.sleep(300)  # Run every 5 minutes
                self._cleanup_old_metrics()
            except Exception as e:
                logger.error(f"Error in metrics cleanup: {e}")
    
    def _cleanup_old_metrics(self):
        """Remove metrics older than retention period."""
        cutoff_time = time.time() - self.RETENTION_DETAILED
        
        with self._metrics_lock:
            # Remove old request metrics
            while self._request_metrics and self._request_metrics[0].timestamp < cutoff_time:
                self._request_metrics.popleft()
        
        logger.debug(f"Metrics cleanup completed, {len(self._request_metrics)} metrics retained")
    
    @classmethod
    def get_thresholds(cls) -> Dict:
        """Get current threshold configuration."""
        return cls.THRESHOLDS.copy()
    
    @classmethod
    def update_threshold(cls, key: str, value: float):
        """Update a specific threshold value."""
        if key in cls.THRESHOLDS:
            cls.THRESHOLDS[key] = value
            logger.info(f"Threshold {key} updated to {value}")


# Global instance
metrics_collector = MetricsCollector()


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance."""
    return metrics_collector

