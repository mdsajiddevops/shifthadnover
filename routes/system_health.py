"""
System Health Dashboard
Shows database status, recent errors, and system uptime
"""

from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user
from models.models import db, User, Team, Shift, Incident
from sqlalchemy import text
from datetime import datetime, timedelta
import logging
import os
import platform

# Try to import psutil, use fallback if not available
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None

logger = logging.getLogger(__name__)

system_health_bp = Blueprint('system_health', __name__)

# Track application start time
APP_START_TIME = datetime.now()


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
    """Get overall system health status."""
    if current_user.role != 'super_admin':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        status = {
            'database': check_database(),
            'memory': check_memory(),
            'disk': check_disk(),
            'uptime': get_uptime(),
            'python_version': platform.python_version(),
            'os_info': f"{platform.system()} {platform.release()}"
        }
        
        # Overall health
        health_score = calculate_health_score(status)
        status['overall_health'] = health_score
        status['health_status'] = 'healthy' if health_score >= 80 else 'warning' if health_score >= 50 else 'critical'
        
        return jsonify({'success': True, 'status': status})
    except Exception as e:
        logger.error(f"Error getting health status: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


def check_database():
    """Check database connection and stats."""
    try:
        # Test connection
        db.session.execute(text('SELECT 1'))
        
        # Get counts
        user_count = User.query.count()
        team_count = Team.query.count()
        shift_count = Shift.query.count()
        incident_count = Incident.query.count()
        
        return {
            'connected': True,
            'status': 'healthy',
            'stats': {
                'users': user_count,
                'teams': team_count,
                'shifts': shift_count,
                'incidents': incident_count
            }
        }
    except Exception as e:
        logger.error(f"Database check failed: {e}")
        return {
            'connected': False,
            'status': 'error',
            'error': str(e)
        }


def check_memory():
    """Check memory usage."""
    if not PSUTIL_AVAILABLE:
        # Try to read from /proc/meminfo on Linux
        try:
            with open('/proc/meminfo', 'r') as f:
                meminfo = {}
                for line in f:
                    parts = line.split(':')
                    if len(parts) == 2:
                        key = parts[0].strip()
                        value = parts[1].strip().split()[0]  # Get numeric value
                        meminfo[key] = int(value) * 1024  # Convert from KB to bytes
                
                total = meminfo.get('MemTotal', 0)
                available = meminfo.get('MemAvailable', meminfo.get('MemFree', 0))
                used = total - available
                percent = round((used / total * 100), 1) if total > 0 else 0
                
                return {
                    'total_gb': round(total / (1024**3), 2),
                    'used_gb': round(used / (1024**3), 2),
                    'available_gb': round(available / (1024**3), 2),
                    'percent_used': percent,
                    'status': 'healthy' if percent < 80 else 'warning' if percent < 90 else 'critical'
                }
        except:
            return {
                'status': 'unavailable', 
                'percent_used': 0, 
                'total_gb': 0, 
                'used_gb': 0, 
                'available_gb': 0,
                'error': 'Memory info not available'
            }
    try:
        memory = psutil.virtual_memory()
        return {
            'total_gb': round(memory.total / (1024**3), 2),
            'used_gb': round(memory.used / (1024**3), 2),
            'available_gb': round(memory.available / (1024**3), 2),
            'percent_used': memory.percent,
            'status': 'healthy' if memory.percent < 80 else 'warning' if memory.percent < 90 else 'critical'
        }
    except:
        return {
            'status': 'unavailable', 
            'percent_used': 0, 
            'total_gb': 0, 
            'used_gb': 0, 
            'available_gb': 0,
            'error': 'Could not retrieve memory info'
        }


def check_disk():
    """Check disk usage."""
    if not PSUTIL_AVAILABLE:
        # Try to read disk stats using os.statvfs on Linux
        try:
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
                'status': 'healthy' if percent < 80 else 'warning' if percent < 90 else 'critical'
            }
        except:
            return {
                'status': 'unavailable', 
                'percent_used': 0, 
                'total_gb': 0, 
                'used_gb': 0, 
                'free_gb': 0,
                'error': 'Disk info not available'
            }
    try:
        disk = psutil.disk_usage('/')
        return {
            'total_gb': round(disk.total / (1024**3), 2),
            'used_gb': round(disk.used / (1024**3), 2),
            'free_gb': round(disk.free / (1024**3), 2),
            'percent_used': round(disk.percent, 1),
            'status': 'healthy' if disk.percent < 80 else 'warning' if disk.percent < 90 else 'critical'
        }
    except:
        return {
            'status': 'unavailable', 
            'percent_used': 0, 
            'total_gb': 0, 
            'used_gb': 0, 
            'free_gb': 0,
            'error': 'Could not retrieve disk info'
        }


def get_uptime():
    """Get application uptime."""
    uptime = datetime.now() - APP_START_TIME
    days = uptime.days
    hours, remainder = divmod(uptime.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    return {
        'started_at': APP_START_TIME.isoformat(),
        'days': days,
        'hours': hours,
        'minutes': minutes,
        'formatted': f"{days}d {hours}h {minutes}m"
    }


def calculate_health_score(status):
    """Calculate overall health score (0-100)."""
    score = 100
    
    # Database (40 points)
    if not status['database'].get('connected'):
        score -= 40
    
    # Memory (30 points)
    mem_percent = status['memory'].get('percent_used', 0)
    if mem_percent > 90:
        score -= 30
    elif mem_percent > 80:
        score -= 15
    
    # Disk (30 points)
    disk_percent = status['disk'].get('percent_used', 0)
    if disk_percent > 90:
        score -= 30
    elif disk_percent > 80:
        score -= 15
    
    return max(0, score)


@system_health_bp.route('/api/system-health/recent-activity')
@login_required
def get_recent_activity():
    """Get recent system activity."""
    if current_user.role != 'super_admin':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        # Recent shifts
        recent_shifts = Shift.query.order_by(Shift.created_at.desc()).limit(5).all()
        
        # Recent incidents
        recent_incidents = Incident.query.order_by(Incident.id.desc()).limit(5).all()
        
        # Recent users
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
    """Get detailed database statistics."""
    if current_user.role != 'super_admin':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
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
        
        # Shifts by status
        from sqlalchemy import func
        shift_status = db.session.query(Shift.status, func.count(Shift.id)).group_by(Shift.status).all()
        stats['shifts_by_status'] = {s[0] or 'unknown': s[1] for s in shift_status}
        
        # Users by role
        user_roles = db.session.query(User.role, func.count(User.id)).group_by(User.role).all()
        stats['users_by_role'] = {r[0] or 'unknown': r[1] for r in user_roles}
        
        return jsonify({'success': True, 'stats': stats})
    except Exception as e:
        logger.error(f"Error getting database stats: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

