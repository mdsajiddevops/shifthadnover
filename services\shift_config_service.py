"""
Shift Configuration Service
Provides centralized access to shift timing and timezone configuration from database
"""

from datetime import time, datetime
import pytz
from flask import current_app
from models.secrets_manager import get_secrets_manager
import logging
logger = logging.getLogger(__name__)

class ShiftConfigService:
    """Service to manage and provide shift configuration from database"""
    
    @staticmethod
    def get_timezone():
        """Get application timezone from configuration"""
        try:
            secrets_manager = get_secrets_manager()
            if secrets_manager:
                timezone_name = secrets_manager.get_secret('app_timezone', 'Asia/Kolkata')
                return pytz.timezone(timezone_name)
            return pytz.timezone('Asia/Kolkata')  # Default fallback
        except Exception as e:
            logger.debug(f"Error getting timezone config: {e}")
            return pytz.timezone('Asia/Kolkata')
    
    @staticmethod
    def get_shift_times():
        """Get shift timing configuration from database"""
        try:
            secrets_manager = get_secrets_manager()
            if secrets_manager:
                return {
                    'day': {
                        'start': secrets_manager.get_secret('day_shift_start', '06:30'),
                        'end': secrets_manager.get_secret('day_shift_end', '15:30'),
                        'code': 'D',
                        'name': 'Day'
                    },
                    'evening': {
                        'start': secrets_manager.get_secret('evening_shift_start', '14:45'),
                        'end': secrets_manager.get_secret('evening_shift_end', '23:45'),
                        'code': 'E', 
                        'name': 'Evening'
                    },
                    'night': {
                        'start': secrets_manager.get_secret('night_shift_start', '21:45'),
                        'end': secrets_manager.get_secret('night_shift_end', '06:45'),
                        'code': 'N',
                        'name': 'Night'
                    },
                    'onshore': {
                        'start': secrets_manager.get_secret('onshore_shift_start', '10:00'),
                        'end': secrets_manager.get_secret('onshore_shift_end', '22:00'),
                        'code': 'OS',
                        'name': 'OnShore'
                    },
                    'offshore': {
                        'start': secrets_manager.get_secret('offshore_shift_start', '22:00'),
                        'end': secrets_manager.get_secret('offshore_shift_end', '10:00'),
                        'code': 'OF',
                        'name': 'OffShore'
                    }
                }
            else:
                # Fallback to hardcoded defaults if secrets manager not available
                return {
                    'day': {'start': '06:30', 'end': '15:30', 'code': 'D', 'name': 'Day'},
                    'evening': {'start': '14:45', 'end': '23:45', 'code': 'E', 'name': 'Evening'},
                    'night': {'start': '21:45', 'end': '06:45', 'code': 'N', 'name': 'Night'},
                    'onshore': {'start': '10:00', 'end': '22:00', 'code': 'OS', 'name': 'OnShore'},
                    'offshore': {'start': '22:00', 'end': '10:00', 'code': 'OF', 'name': 'OffShore'}
                }
        except Exception as e:
            logger.debug(f"Error getting shift times config: {e}")
            # Return hardcoded defaults on error
            return {
                'day': {'start': '06:30', 'end': '15:30', 'code': 'D', 'name': 'Day'},
                'evening': {'start': '14:45', 'end': '23:45', 'code': 'E', 'name': 'Evening'},
                'night': {'start': '21:45', 'end': '06:45', 'code': 'N', 'name': 'Night'},
                'onshore': {'start': '10:00', 'end': '22:00', 'code': 'OS', 'name': 'OnShore'},
                'offshore': {'start': '22:00', 'end': '10:00', 'code': 'OF', 'name': 'OffShore'}
            }
    
    @staticmethod
    def parse_time_string(time_str):
        """Parse time string (HH:MM) to time object"""
        try:
            hour, minute = time_str.split(':')
            return time(int(hour), int(minute))
        except (ValueError, AttributeError):
            return None
    
    @staticmethod
    def get_shift_times_as_time_objects():
        """Get shift timing configuration as time objects for easy comparison"""
        shift_times = ShiftConfigService.get_shift_times()
        
        return {
            'day': {
                'start': ShiftConfigService.parse_time_string(shift_times['day']['start']),
                'end': ShiftConfigService.parse_time_string(shift_times['day']['end']),
                'code': 'D',
                'name': 'Day'
            },
            'evening': {
                'start': ShiftConfigService.parse_time_string(shift_times['evening']['start']),
                'end': ShiftConfigService.parse_time_string(shift_times['evening']['end']),
                'code': 'E',
                'name': 'Evening'
            },
            'night': {
                'start': ShiftConfigService.parse_time_string(shift_times['night']['start']),
                'end': ShiftConfigService.parse_time_string(shift_times['night']['end']),
                'code': 'N',
                'name': 'Night'
            }
        }
    
    @staticmethod
    def get_current_shift_type(current_time=None):
        """
        Determine current shift type based on time and configuration
        
        Args:
            current_time: datetime object (optional, defaults to now in app timezone)
            
        Returns:
            tuple: (current_shift_type, next_shift_type)
        """
        try:
            if current_time is None:
                app_timezone = ShiftConfigService.get_timezone()
                current_time = datetime.now(app_timezone)
            
            shift_times = ShiftConfigService.get_shift_times_as_time_objects()
            current_time_only = current_time.time()
            
            # Day shift
            if (shift_times['day']['start'] <= current_time_only < shift_times['day']['end']):
                return 'Morning', 'Evening'
            
            # Evening shift  
            elif (shift_times['evening']['start'] <= current_time_only < shift_times['evening']['end']):
                return 'Evening', 'Night'
            
            # Night shift (crosses midnight)
            else:
                return 'Night', 'Morning'
                
        except Exception as e:
            logger.debug(f"Error determining current shift: {e}")
            # Fallback to hardcoded logic
            t = current_time.time() if current_time else datetime.now().time()
            if time(6,30) <= t < time(15,30):
                return 'Morning', 'Evening'
            elif time(14,45) <= t < time(23,45):
                return 'Evening', 'Night'
            else:
                return 'Night', 'Morning'
    
    @staticmethod
    def get_shift_code_for_type(shift_type):
        """Convert shift type to shift code"""
        shift_map = {
            'Morning': 'D',
            'Day': 'D', 
            'Evening': 'E',
            'Night': 'N',
            'OnShore': 'OS',
            'OffShore': 'OF'
        }
        return shift_map.get(shift_type, 'D')

# Global instance for easy import
shift_config_service = ShiftConfigService()