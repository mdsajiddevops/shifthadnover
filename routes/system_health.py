"""
System Health Dashboard - Enterprise Grade
Provides comprehensive system monitoring including:
- Application performance metrics (RPS, response times, error rates)
- Database health (connections, latency, slow queries)
- Container and runtime status
- Resource usage with thresholds
- Historical trends for sparklines
"""

from flask import Blueprint, render_template, jsonify, request, g
from flask_login import login_required, current_user
from models.models import db, User, Team, Shift, Incident
from sqlalchemy import text
from datetime import datetime, timedelta
from functools import wraps
import logging
import os
import platform
import threading
import socket
import time

# Try to import psutil for system metrics
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None

# Import metrics collector
try:
    from services.metrics_collector import get_metrics_collector, MetricsCollector
    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False
    get_metrics_collector = None

logger = logging.getLogger(__name__)

system_health_bp = Blueprint('system_health', __name__)

# Track application start time
APP_START_TIME = datetime.now()

# ============================================================================
# CONFIGURATION & THRESHOLDS
# ============================================================================

HEALTH_THRESHOLDS = {
    'cpu': {'warning': 70, 'critical': 90},
    'memory': {'warning': 80, 'critical': 95},
    'disk': {'warning': 80, 'critical': 95},
    'error_rate': {'warning': 1.0, 'critical': 5.0},
    'response_time': {'warning': 500, 'critical': 2000},
    'db_connections': {'warning': 80, 'critical': 95},
    'db_latency': {'warning': 100, 'critical': 500},
}


def get_status_from_value(value: float, metric_type: str) -> str:
    """Determine health status based on value and thresholds."""
    thresholds = HEALTH_THRESHOLDS.get(metric_type, {'warning': 70, 'critical': 90})
    if value >= thresholds['critical']:
        return 'critical'
    elif value >= thresholds['warning']:
        return 'warning'
    return 'healthy'


# ============================================================================
# MIDDLEWARE FOR REQUEST METRICS
# ============================================================================

@system_health_bp.before_app_request
def before_request_metrics():
    """Record request start time for metrics collection."""
    g.request_start_time = time.time()


@system_health_bp.after_app_request
def after_request_metrics(response):
    """Record request metrics after response."""
    if METRICS_AVAILABLE and hasattr(g, 'request_start_time'):
        try:
            response_time_ms = (time.time() - g.request_start_time) * 1000
            collector = get_metrics_collector()
            collector.record_request(
                path=request.path,
                method=request.method,
                status_code=response.status_code,
                response_time_ms=response_time_ms
            )
        except Exception as e:
            logger.debug(f"Error recording request metrics: {e}")
    return response


# ============================================================================
# ROUTES
# ============================================================================

@system_health_bp.route('/admin/system-health')
@login_required
def system_health():
    """System health dashboard page."""
    if current_user.role != 'super_admin':
        return "Access denied - Super Admin only", 403
    return render_template('admin/system_health.html')


@system_health_bp.route('/api/system-health/status')
@login_required
def get_health_status():
    """
    Comprehensive health status API.
    Returns all system metrics in a structured format.
    """
    if current_user.role != 'super_admin':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        # Collect all metrics
        status = {
            'timestamp': datetime.now().isoformat(),
            'system': get_system_metrics(),
            'database': get_database_metrics(),
            'application': get_application_metrics(),
            'services': get_services_status(),
            'network': get_network_status(),
            'thresholds': HEALTH_THRESHOLDS
        }
        
        # Calculate overall health
        status['overall_health'] = calculate_overall_health(status)
        status['health_status'] = status['overall_health']['status']
        status['overall_score'] = status['overall_health']['score']
        
        # Legacy compatibility fields
        status['uptime'] = status['application'].get('uptime', {})
        status['python_version'] = platform.python_version()
        status['os_info'] = f"{platform.system()} {platform.release()}"
        status['memory'] = status['system'].get('memory', {})
        status['disk'] = status['system'].get('disk', {})
        status['cpu'] = status['system'].get('cpu', {})
        status['threads'] = status['application'].get('threads', {})
        
        return jsonify({'success': True, 'status': status})
    except Exception as e:
        logger.error(f"Error getting health status: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@system_health_bp.route('/api/system-health/performance')
@login_required
def get_performance_metrics():
    """Get application performance metrics (RPS, response times, errors)."""
    if current_user.role != 'super_admin':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        if not METRICS_AVAILABLE:
            return jsonify({
                'success': True,
                'metrics': get_fallback_performance_metrics()
            })
        
        collector = get_metrics_collector()
        summary = collector.get_summary(window_seconds=60)
        
        return jsonify({
            'success': True,
            'metrics': {
                'requests_per_second': round(summary.requests_per_second, 2),
                'total_requests': summary.total_requests,
                'error_count_4xx': summary.error_count_4xx,
                'error_count_5xx': summary.error_count_5xx,
                'error_rate': round(summary.error_rate, 2),
                'avg_response_time_ms': round(summary.avg_response_time_ms, 2),
                'p95_response_time_ms': round(summary.p95_response_time_ms, 2),
                'p99_response_time_ms': round(summary.p99_response_time_ms, 2),
                'min_response_time_ms': round(summary.min_response_time_ms, 2),
                'max_response_time_ms': round(summary.max_response_time_ms, 2),
                'failed_requests_1h': summary.failed_requests_1h,
                'status': get_status_from_value(summary.error_rate, 'error_rate')
            }
        })
    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@system_health_bp.route('/api/system-health/sparklines')
@login_required
def get_sparkline_data():
    """Get historical data for sparkline charts."""
    if current_user.role != 'super_admin':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        if not METRICS_AVAILABLE:
            return jsonify({
                'success': True,
                'sparklines': get_fallback_sparklines()
            })
        
        collector = get_metrics_collector()
        data = collector.get_sparkline_data()
        
        return jsonify({
            'success': True,
            'sparklines': {
                'cpu': [d['value'] for d in data.get('cpu', [])],
                'memory': [d['value'] for d in data.get('memory', [])],
                'rps': [d['value'] for d in data.get('rps', [])],
                'error_rate': [d['value'] for d in data.get('error_rate', [])],
                'response_time': [d['value'] for d in data.get('response_time', [])]
            }
        })
    except Exception as e:
        logger.error(f"Error getting sparkline data: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@system_health_bp.route('/health')
def health_check():
    """
    Simple health check endpoint for load balancers and monitoring tools.
    Returns minimal response for fast checks.
    """
    try:
        # Quick database check
        db.session.execute(text('SELECT 1'))
        db_healthy = True
    except:
        db_healthy = False
    
    status = 'healthy' if db_healthy else 'unhealthy'
    status_code = 200 if db_healthy else 503
    
    return jsonify({
        'status': status,
        'timestamp': datetime.now().isoformat(),
        'database': 'connected' if db_healthy else 'disconnected'
    }), status_code


@system_health_bp.route('/api/system-health/thresholds', methods=['GET', 'POST'])
@login_required
def manage_thresholds():
    """Get or update health thresholds."""
    if current_user.role != 'super_admin':
        return jsonify({'error': 'Access denied'}), 403
    
    if request.method == 'GET':
        return jsonify({'success': True, 'thresholds': HEALTH_THRESHOLDS})
    
    try:
        data = request.get_json()
        for metric, values in data.items():
            if metric in HEALTH_THRESHOLDS:
                if 'warning' in values:
                    HEALTH_THRESHOLDS[metric]['warning'] = float(values['warning'])
                if 'critical' in values:
                    HEALTH_THRESHOLDS[metric]['critical'] = float(values['critical'])
        
        return jsonify({'success': True, 'thresholds': HEALTH_THRESHOLDS})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


# ============================================================================
# METRIC COLLECTION FUNCTIONS
# ============================================================================

def get_system_metrics() -> dict:
    """Get system resource metrics (CPU, Memory, Disk)."""
    return {
        'cpu': get_cpu_metrics(),
        'memory': get_memory_metrics(),
        'disk': get_disk_metrics()
    }


def get_cpu_metrics() -> dict:
    """Get CPU usage metrics."""
    try:
        if PSUTIL_AVAILABLE:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            cpu_count = psutil.cpu_count()
            load_avg = os.getloadavg() if hasattr(os, 'getloadavg') else (0, 0, 0)
        else:
            # Fallback for Linux
            cpu_count = os.cpu_count() or 1
            try:
                with open('/proc/loadavg', 'r') as f:
                    parts = f.read().strip().split()
                    load_avg = (float(parts[0]), float(parts[1]), float(parts[2]))
                    cpu_percent = round((load_avg[0] / cpu_count) * 100, 1)
            except:
                cpu_percent = 0
                load_avg = (0, 0, 0)
        
        return {
            'percent': min(cpu_percent, 100),
            'cores': cpu_count,
            'load_1min': round(load_avg[0], 2),
            'load_5min': round(load_avg[1], 2),
            'load_15min': round(load_avg[2], 2),
            'status': get_status_from_value(cpu_percent, 'cpu')
        }
    except Exception as e:
        logger.error(f"Error getting CPU metrics: {e}")
        return {'percent': 0, 'cores': 1, 'status': 'unknown', 'error': str(e)}


def get_memory_metrics() -> dict:
    """Get memory usage metrics."""
    try:
        if PSUTIL_AVAILABLE:
            mem = psutil.virtual_memory()
            return {
                'total_gb': round(mem.total / (1024**3), 2),
                'used_gb': round(mem.used / (1024**3), 2),
                'available_gb': round(mem.available / (1024**3), 2),
                'percent_used': mem.percent,
                'status': get_status_from_value(mem.percent, 'memory')
            }
        else:
            # Fallback for Linux
            with open('/proc/meminfo', 'r') as f:
                meminfo = {}
                for line in f:
                    parts = line.split(':')
                    if len(parts) == 2:
                        key = parts[0].strip()
                        value = int(parts[1].strip().split()[0]) * 1024
                        meminfo[key] = value
                
                total = meminfo.get('MemTotal', 0)
                available = meminfo.get('MemAvailable', meminfo.get('MemFree', 0))
                used = total - available
                percent = round((used / total * 100), 1) if total > 0 else 0
                
                return {
                    'total_gb': round(total / (1024**3), 2),
                    'used_gb': round(used / (1024**3), 2),
                    'available_gb': round(available / (1024**3), 2),
                    'percent_used': percent,
                    'status': get_status_from_value(percent, 'memory')
                }
    except Exception as e:
        logger.error(f"Error getting memory metrics: {e}")
        return {'percent_used': 0, 'status': 'unknown', 'error': str(e)}


def get_disk_metrics() -> dict:
    """Get disk usage metrics."""
    try:
        if PSUTIL_AVAILABLE:
            disk = psutil.disk_usage('/')
            return {
                'total_gb': round(disk.total / (1024**3), 2),
                'used_gb': round(disk.used / (1024**3), 2),
                'free_gb': round(disk.free / (1024**3), 2),
                'percent_used': round(disk.percent, 1),
                'status': get_status_from_value(disk.percent, 'disk')
            }
        else:
            # Fallback for Linux
            stat = os.statvfs('/')
            total = stat.f_blocks * stat.f_frsize
            free = stat.f_bavail * stat.f_frsize
            used = total - free
            percent = round((used / total * 100), 1) if total > 0 else 0
            
            return {
                'total_gb': round(total / (1024**3), 2),
                'used_gb': round(used / (1024**3), 2),
                'free_gb': round(free / (1024**3), 2),
                'percent_used': percent,
                'status': get_status_from_value(percent, 'disk')
            }
    except Exception as e:
        logger.error(f"Error getting disk metrics: {e}")
        return {'percent_used': 0, 'status': 'unknown', 'error': str(e)}


def get_database_metrics() -> dict:
    """Get comprehensive database health metrics."""
    result = {
        'connected': False,
        'status': 'unknown',
        'stats': {},
        'connections': {},
        'latency_ms': 0,
        'slow_queries': 0,
        'errors': 0
    }
    
    try:
        # Test connection and measure latency
        start_time = time.time()
        db.session.execute(text('SELECT 1'))
        result['latency_ms'] = round((time.time() - start_time) * 1000, 2)
        result['connected'] = True
        
        # Get table counts
        result['stats'] = {
            'users': User.query.count(),
            'teams': Team.query.count(),
            'shifts': Shift.query.count(),
            'incidents': Incident.query.count()
        }
        
        # Get connection info (MySQL specific)
        try:
            conn_result = db.session.execute(text("SHOW STATUS LIKE 'Threads_connected'"))
            row = conn_result.fetchone()
            active_connections = int(row[1]) if row else 0
            
            max_result = db.session.execute(text("SHOW VARIABLES LIKE 'max_connections'"))
            row = max_result.fetchone()
            max_connections = int(row[1]) if row else 100
            
            connection_percent = round((active_connections / max_connections) * 100, 1)
            
            result['connections'] = {
                'active': active_connections,
                'max': max_connections,
                'percent': connection_percent,
                'status': get_status_from_value(connection_percent, 'db_connections')
            }
        except Exception as e:
            logger.debug(f"Could not get MySQL connection info: {e}")
            result['connections'] = {'active': 0, 'max': 100, 'percent': 0, 'status': 'unknown'}
        
        # Get slow query count (last hour)
        try:
            slow_result = db.session.execute(text("SHOW GLOBAL STATUS LIKE 'Slow_queries'"))
            row = slow_result.fetchone()
            result['slow_queries'] = int(row[1]) if row else 0
        except:
            result['slow_queries'] = 0
        
        # Determine overall database status
        latency_status = get_status_from_value(result['latency_ms'], 'db_latency')
        conn_status = result['connections'].get('status', 'healthy')
        
        if latency_status == 'critical' or conn_status == 'critical':
            result['status'] = 'critical'
        elif latency_status == 'warning' or conn_status == 'warning':
            result['status'] = 'warning'
        else:
            result['status'] = 'healthy'
            
    except Exception as e:
        logger.error(f"Database check failed: {e}")
        result['status'] = 'error'
        result['error'] = str(e)
    
    return result


def get_application_metrics() -> dict:
    """Get application runtime metrics."""
    # Uptime calculation
    uptime_delta = datetime.now() - APP_START_TIME
    uptime_seconds = uptime_delta.total_seconds()
    days, remainder = divmod(int(uptime_seconds), 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    result = {
        'uptime': {
            'started_at': APP_START_TIME.isoformat(),
            'days': days,
            'hours': hours,
            'minutes': minutes,
            'seconds': seconds,
            'formatted': f"{days}d {hours}h {minutes}m",
            'total_seconds': uptime_seconds
        },
        'threads': {
            'active_count': threading.active_count(),
            'status': 'healthy' if threading.active_count() < 50 else 'warning'
        },
        'process': get_process_metrics(),
        'workers': get_worker_info(),
        'performance': get_fallback_performance_metrics()
    }
    
    # Add metrics from collector if available
    if METRICS_AVAILABLE:
        try:
            collector = get_metrics_collector()
            summary = collector.get_summary(60)
            result['performance'] = {
                'requests_per_second': round(summary.requests_per_second, 2),
                'error_rate': round(summary.error_rate, 2),
                'avg_response_time_ms': round(summary.avg_response_time_ms, 2),
                'p95_response_time_ms': round(summary.p95_response_time_ms, 2),
                'failed_requests_1h': summary.failed_requests_1h,
                'status': get_status_from_value(summary.error_rate, 'error_rate')
            }
        except Exception as e:
            logger.debug(f"Could not get performance metrics: {e}")
    
    return result


def get_process_metrics() -> dict:
    """Get current process metrics."""
    try:
        pid = os.getpid()
        process_memory = 0
        open_fds = 0
        
        # Get process memory
        try:
            with open(f'/proc/{pid}/status', 'r') as f:
                for line in f:
                    if line.startswith('VmRSS:'):
                        process_memory = int(line.split()[1]) * 1024
                        break
        except:
            if PSUTIL_AVAILABLE:
                process = psutil.Process(pid)
                process_memory = process.memory_info().rss
        
        # Get open file descriptors
        try:
            open_fds = len(os.listdir(f'/proc/{pid}/fd'))
        except:
            pass
        
        return {
            'pid': pid,
            'memory_mb': round(process_memory / (1024 * 1024), 2),
            'open_files': open_fds,
            'status': 'running'
        }
    except Exception as e:
        return {'pid': os.getpid(), 'status': 'error', 'error': str(e)}


def get_worker_info() -> dict:
    """Get WSGI worker information."""
    try:
        worker_type = 'development'
        worker_count = 1
        
        # Check for Gunicorn
        try:
            for proc_id in os.listdir('/proc'):
                if proc_id.isdigit():
                    try:
                        with open(f'/proc/{proc_id}/cmdline', 'r') as f:
                            cmdline = f.read()
                            if 'gunicorn' in cmdline:
                                worker_type = 'gunicorn'
                                worker_count += 1
                    except:
                        pass
        except:
            pass
        
        return {
            'type': worker_type,
            'count': worker_count,
            'status': 'running'
        }
    except:
        return {'type': 'unknown', 'count': 0, 'status': 'unknown'}


def get_services_status() -> dict:
    """Get status of related services."""
    return {
        'flask_app': {
            'name': 'Flask Application',
            'status': 'running',
            'healthy': True,
            'port': 5000
        },
        'nginx': {
            'name': 'Nginx Proxy',
            'status': 'running',
            'healthy': True,
            'note': 'Inferred from page access'
        },
        'database_network': check_database_network(),
        'container': get_container_status(),
        'containers': get_all_containers()
    }


def check_database_network() -> dict:
    """Check database network connectivity."""
    db_host = os.environ.get('DB_HOST', 'shift-db')
    db_port = int(os.environ.get('DB_PORT', 3306))
    
    try:
        start_time = time.time()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((db_host, db_port))
        sock.close()
        response_time = round((time.time() - start_time) * 1000, 2)
        
        return {
            'name': 'MySQL',
            'status': 'running' if result == 0 else 'not responding',
            'healthy': result == 0,
            'port': db_port,
            'response_time_ms': response_time
        }
    except Exception as e:
        return {'name': 'MySQL', 'status': 'error', 'healthy': False, 'error': str(e)}


def get_container_status() -> dict:
    """Get current container status."""
    try:
        is_docker = os.path.exists('/.dockerenv')
        container_id = socket.gethostname()[:12] if is_docker else None
        
        # Get process count
        try:
            process_count = len([p for p in os.listdir('/proc') if p.isdigit()])
        except:
            process_count = 0
        
        return {
            'name': 'shift-web',
            'type': 'Web Application',
            'is_docker': is_docker,
            'container_id': container_id or 'native',
            'status': 'running',
            'healthy': True,
            'process_count': process_count
        }
    except Exception as e:
        return {'name': 'shift-web', 'status': 'unknown', 'healthy': True, 'error': str(e)}


def get_all_containers() -> list:
    """Get status of all known containers."""
    containers = []
    
    # Web container (self)
    web = get_container_status()
    web['port'] = 5000
    containers.append(web)
    
    # Database container
    db_status = check_database_network()
    containers.append({
        'name': 'shift-db',
        'type': 'MySQL Database',
        'is_docker': True,
        'container_id': os.environ.get('DB_HOST', 'shift-db'),
        'status': db_status['status'],
        'healthy': db_status['healthy'],
        'port': db_status.get('port', 3306),
        'response_time_ms': db_status.get('response_time_ms', 0)
    })
    
    return containers


def get_network_status() -> dict:
    """Get network connectivity status."""
    result = {
        'internal_network': True,
        'dns_resolution': False,
        'internet_access': False,
        'status': 'healthy'
    }
    
    # Check DNS
    try:
        socket.setdefaulttimeout(1)
        socket.gethostbyname('google.com')
        result['dns_resolution'] = True
        result['internet_access'] = True
    except:
        try:
            db_host = os.environ.get('DB_HOST', 'shift-db')
            socket.gethostbyname(db_host)
            result['dns_resolution'] = True
        except:
            pass
    
    return result


def calculate_overall_health(status: dict) -> dict:
    """Calculate overall system health score and status."""
    score = 100
    issues = []
    
    # CPU (15 points)
    cpu_status = status.get('system', {}).get('cpu', {}).get('status', 'healthy')
    if cpu_status == 'critical':
        score -= 15
        issues.append('CPU usage critical')
    elif cpu_status == 'warning':
        score -= 7
        issues.append('CPU usage high')
    
    # Memory (20 points)
    mem_status = status.get('system', {}).get('memory', {}).get('status', 'healthy')
    if mem_status == 'critical':
        score -= 20
        issues.append('Memory usage critical')
    elif mem_status == 'warning':
        score -= 10
        issues.append('Memory usage high')
    
    # Disk (15 points)
    disk_status = status.get('system', {}).get('disk', {}).get('status', 'healthy')
    if disk_status == 'critical':
        score -= 15
        issues.append('Disk usage critical')
    elif disk_status == 'warning':
        score -= 7
        issues.append('Disk usage high')
    
    # Database (30 points)
    db_status = status.get('database', {}).get('status', 'healthy')
    if db_status == 'error' or db_status == 'critical':
        score -= 30
        issues.append('Database issues')
    elif db_status == 'warning':
        score -= 15
        issues.append('Database performance degraded')
    
    # Application (20 points)
    perf = status.get('application', {}).get('performance', {})
    if perf.get('status') == 'critical':
        score -= 20
        issues.append('High error rate')
    elif perf.get('status') == 'warning':
        score -= 10
        issues.append('Elevated error rate')
    
    # Determine overall status
    if score >= 80:
        overall_status = 'healthy'
    elif score >= 50:
        overall_status = 'warning'
    else:
        overall_status = 'critical'
    
    return {
        'score': max(0, score),
        'status': overall_status,
        'issues': issues
    }


def get_fallback_performance_metrics() -> dict:
    """Get fallback performance metrics when collector is not available."""
    return {
        'requests_per_second': 0,
        'error_rate': 0,
        'avg_response_time_ms': 0,
        'p95_response_time_ms': 0,
        'failed_requests_1h': 0,
        'status': 'healthy'
    }


def get_fallback_sparklines() -> dict:
    """Get empty sparkline data when collector is not available."""
    return {
        'cpu': [],
        'memory': [],
        'rps': [],
        'error_rate': [],
        'response_time': []
    }


# ============================================================================
# LEGACY COMPATIBILITY ROUTES
# ============================================================================

@system_health_bp.route('/api/system-health/recent-activity')
@login_required
def get_recent_activity():
    """Get recent system activity (legacy endpoint)."""
    if current_user.role != 'super_admin':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        recent_shifts = Shift.query.order_by(Shift.created_at.desc()).limit(5).all()
        recent_incidents = Incident.query.order_by(Incident.id.desc()).limit(5).all()
        recent_users = User.query.order_by(User.id.desc()).limit(5).all()
        
        return jsonify({
            'success': True,
            'activity': {
                'recent_shifts': [{
                    'id': s.id,
                    'date': s.date.isoformat() if s.date else None,
                    'shift_type': s.shift_type,
                    'status': s.status
                } for s in recent_shifts],
                'recent_incidents': [{
                    'id': i.id,
                    'title': i.title[:50] if i.title else 'N/A',
                    'status': i.status,
                    'priority': i.priority
                } for i in recent_incidents],
                'recent_users': [{
                    'id': u.id,
                    'username': u.username,
                    'role': u.role
                } for u in recent_users]
            }
        })
    except Exception as e:
        logger.error(f"Error getting recent activity: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@system_health_bp.route('/api/system-health/database-stats')
@login_required
def get_database_stats():
    """Get detailed database statistics (legacy endpoint)."""
    if current_user.role != 'super_admin':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        from sqlalchemy import func
        
        stats = {
            'tables': {
                'users': User.query.count(),
                'teams': Team.query.count(),
                'shifts': Shift.query.count(),
                'incidents': Incident.query.count()
            },
            'shifts_by_status': {},
            'users_by_role': {}
        }
        
        shift_status = db.session.query(Shift.status, func.count(Shift.id)).group_by(Shift.status).all()
        stats['shifts_by_status'] = {s[0] or 'unknown': s[1] for s in shift_status}
        
        user_roles = db.session.query(User.role, func.count(User.id)).group_by(User.role).all()
        stats['users_by_role'] = {r[0] or 'unknown': r[1] for r in user_roles}
        
        return jsonify({'success': True, 'stats': stats})
    except Exception as e:
        logger.error(f"Error getting database stats: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
