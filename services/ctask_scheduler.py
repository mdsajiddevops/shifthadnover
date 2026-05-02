"""
CTask Auto-Assignment Scheduler
Automatically processes unassigned CTasks at regular intervals
"""
import threading
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List

# Module-level Celery instance so tests can patch services.ctask_scheduler.celery.
try:
    from celery_app import celery
except Exception:
    celery = None  # type: ignore[assignment]

# Module-level task reference so tests can patch services.ctask_scheduler.run_ctask_assignment.
try:
    from tasks.ctask_tasks import run_ctask_assignment
except Exception:
    run_ctask_assignment = None  # type: ignore[assignment]

class CTaskScheduler:
    def __init__(self, check_interval_minutes: int = 2):
        """
        Initialize the CTask scheduler
        
        Args:
            check_interval_minutes: How often to check for unassigned CTasks (default: 2 minutes for faster response)
        """
        self.logger = logging.getLogger(__name__)
        self.check_interval = check_interval_minutes * 60  # Convert to seconds
        self.running = False
        self.thread = None
        self.assignment_service = None  # Initialize later
        self.last_check = None
        self.processed_ctasks = set()  # Track processed CTasks to avoid duplicates
        
    def start(self):
        """Start the automatic CTask processing"""
        if self.running:
            self.logger.warning("CTask scheduler already running")
            return
            
        self.running = True
        self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.thread.start()
        self.logger.info(f"🚀 CTask scheduler started - checking every {self.check_interval//60} minutes for automatic assignment")
        
        # Log startup message
        from services.console_service import console
        console.info(f"🚀 CTask Auto-Assignment Scheduler Started", {
            'check_interval_minutes': self.check_interval//60,
            'description': 'Monitoring ServiceNow for unassigned CTasks and automatically assigning them to on-shift engineers'
        })
        
    def stop(self):
        """Stop the automatic CTask processing"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        self.logger.info("CTask scheduler stopped")
        
    def _run_scheduler(self):
        """Main scheduler loop"""
        while self.running:
            try:
                # Import app instance from the main module 
                from app import app
                
                # Use app context for database operations
                with app.app_context():
                    self.process_unassigned_ctasks()
                
                # Wait for the next check interval
                time.sleep(self.check_interval)
                
            except Exception as e:
                self.logger.error(f"Error in CTask scheduler: {str(e)}")
                # Sleep for a shorter interval on error to retry sooner
                time.sleep(30)
    
    def process_unassigned_ctasks(self) -> Dict:
        """
        Process all unassigned CTasks
        
        Returns:
            Dict with processing results
        """
        try:
            start_time = datetime.now()
            self.logger.info("Starting automatic CTask assignment check...")
            
            # Initialize assignment service if not already done
            if not self.assignment_service:
                from services.ctask_assignment_service import CTaskAssignmentService
                self.assignment_service = CTaskAssignmentService()
            
            # Process pending CTasks
            results = self.assignment_service.process_pending_ctasks()
            
            # Calculate summary
            total_processed = len(results)
            successful_assignments = len([r for r in results if r.get('success', False)])
            failed_assignments = total_processed - successful_assignments
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Log the results
            summary = {
                'timestamp': start_time.isoformat(),
                'total_processed': total_processed,
                'successful_assignments': successful_assignments,
                'failed_assignments': failed_assignments,
                'processing_time_seconds': processing_time,
                'results': results
            }
            
            if total_processed > 0:
                self.logger.info(f"CTask assignment check completed: {successful_assignments}/{total_processed} successful assignments")
                
                # Skip audit logging to avoid errors for now
                self.logger.info(f"Assignment summary: {successful_assignments} successful, {failed_assignments} failed")
            else:
                self.logger.debug("No unassigned CTasks found")
            
            self.last_check = start_time
            return summary
            
        except Exception as e:
            self.logger.error(f"Error processing unassigned CTasks: {str(e)}")
            return {
                'timestamp': datetime.now().isoformat(),
                'error': str(e),
                'total_processed': 0,
                'successful_assignments': 0,
                'failed_assignments': 0
            }
    
    def get_status(self) -> Dict:
        """
        Get scheduler status
        
        Returns:
            Dict with current status
        """
        return {
            'running': self.running,
            'check_interval_minutes': self.check_interval // 60,
            'last_check': self.last_check.isoformat() if self.last_check else None,
            'next_check': (self.last_check + timedelta(seconds=self.check_interval)).isoformat() if self.last_check else None
        }
    
    def force_check(self) -> Dict:
        """
        Force an immediate check for unassigned CTasks
        
        Returns:
            Dict with processing results
        """
        self.logger.info("Forcing immediate CTask assignment check...")
        
        # Initialize assignment service if not already done
        if not self.assignment_service:
            from services.ctask_assignment_service import CTaskAssignmentService
            self.assignment_service = CTaskAssignmentService()

        return self.process_unassigned_ctasks()

# ---------------------------------------------------------------------------
# Celery-backed public API
# The CTaskScheduler threading class above is kept for reference but is no
# longer started in-process. All periodic execution is handled by the Celery
# beat scheduler (celery_app.py + tasks.py). These functions preserve the
# same signatures so routes/ctask_assignment.py requires no changes.
# ---------------------------------------------------------------------------

_scheduler_logger = logging.getLogger(__name__)


def start_ctask_scheduler():
    """No-op — Celery Beat manages scheduling. Workers are started via docker-compose."""
    _scheduler_logger.info(
        "start_ctask_scheduler called — scheduling is managed by Celery Beat, no action needed."
    )


def stop_ctask_scheduler():
    """No-op — stop the Celery worker via docker-compose to pause scheduling."""
    _scheduler_logger.info(
        "stop_ctask_scheduler called — to pause scheduling, stop the celery-beat container."
    )

def get_scheduler_status():
    """Return Celery worker availability as scheduler status.

    Completes within 5 seconds regardless of broker availability (REQ-013).
    Returns a structured dict — never raises (REQ-004).
    """
    try:
        # inspect timeout kept well under the 5 s budget (REQ-013).
        inspect = celery.control.inspect(timeout=2.0)
        active = inspect.active() or {}
        workers_up = len(active) > 0
        return {
            'running': workers_up,
            'status': 'Running' if workers_up else 'Stopped (no Celery workers)',
            'workers': list(active.keys()),
            'last_check': None,
            'next_check': None,
            'engine': 'celery',
        }
    except Exception as e:
        # Broker unreachable — return degraded dict, do not raise (REQ-004).
        return {
            'running': False,
            'status': f'Unknown — Celery broker unreachable: {e}',
            'workers': [],
            'engine': 'celery',
            'broker_error': str(e),
        }


def force_scheduler_check():
    """Dispatch an immediate CTask assignment task via Celery."""
    result = run_ctask_assignment.delay()
    return {
        'dispatched': True,
        'task_id': result.id,
        'message': 'CTask assignment task queued on Celery worker',
    }