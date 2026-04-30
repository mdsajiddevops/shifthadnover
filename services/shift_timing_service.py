"""
Shift Timing Service
Business logic for managing team-specific shift timing configurations
"""

from datetime import datetime, time
from typing import Dict, List, Optional
import logging

from models.models import db, Account, Team
from models.team_shift_timing_config import TeamShiftTimingConfig

logger = logging.getLogger(__name__)

class ShiftTimingService:
    """Service for managing shift timing configurations"""
    
    def __init__(self):
        self.logger = logger

    def get_team_configurations(self, account_id: int, team_id: int, active_only: bool = True) -> Dict:
        """Get all shift configurations for a team"""
        try:
            # Validate that account and team exist
            account = Account.query.get(account_id)
            if not account:
                return {
                    'success': False,
                    'error': 'Account not found'
                }
            
            team = Team.query.filter_by(id=team_id, account_id=account_id).first()
            if not team:
                return {
                    'success': False,
                    'error': 'Team not found or does not belong to this account'
                }
            
            # Get configurations
            configurations = TeamShiftTimingConfig.get_account_team_shifts(
                account_id=account_id,
                team_id=team_id,
                active_only=active_only
            )
            
            return {
                'success': True,
                'account': {
                    'id': account.id,
                    'name': account.name
                },
                'team': {
                    'id': team.id,
                    'name': team.name
                },
                'configurations': [config.to_dict() for config in configurations],
                'total': len(configurations)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting team configurations: {str(e)}")
            return {
                'success': False,
                'error': 'An error occurred while retrieving configurations'
            }

    def create_configuration(self, config_data: Dict, created_by: str) -> Dict:
        """Create a new shift configuration"""
        try:
            # Validate required fields
            required_fields = ['account_id', 'team_id', 'shift_code', 'shift_name', 'start_time', 'end_time']
            for field in required_fields:
                if field not in config_data:
                    return {
                        'success': False,
                        'error': f'Missing required field: {field}'
                    }
            
            # Validate that account and team exist
            account = Account.query.get(config_data['account_id'])
            if not account:
                return {
                    'success': False,
                    'error': 'Account not found'
                }
            
            team = Team.query.filter_by(
                id=config_data['team_id'], 
                account_id=config_data['account_id']
            ).first()
            if not team:
                return {
                    'success': False,
                    'error': 'Team not found or does not belong to this account'
                }
            
            # Check for duplicate shift codes within the same team
            existing_config = TeamShiftTimingConfig.query.filter_by(
                team_id=config_data['team_id'],
                account_id=config_data['account_id'],
                shift_code=config_data['shift_code'].upper(),
                is_active=True
            ).first()
            
            if existing_config:
                return {
                    'success': False,
                    'error': f'Shift code "{config_data["shift_code"]}" already exists for this team'
                }
            
            # Parse and validate time strings
            try:
                start_time = datetime.strptime(config_data['start_time'], '%H:%M').time()
                end_time = datetime.strptime(config_data['end_time'], '%H:%M').time()
            except ValueError as ve:
                return {
                    'success': False,
                    'error': f'Invalid time format. Use HH:MM format. Error: {str(ve)}'
                }
            
            # Overlap validation disabled - allow overlapping shifts
            # This allows for shift handovers, peak coverage, and flexible scheduling
            
            # Create the configuration
            new_config = TeamShiftTimingConfig(
                account_id=config_data['account_id'],
                team_id=config_data['team_id'],
                shift_code=config_data['shift_code'].upper(),
                shift_name=config_data['shift_name'].strip(),
                start_time=start_time,
                end_time=end_time,
                color_code=config_data.get('color_code', '#007bff'),
                order_index=config_data.get('order_index', 0),
                is_active=config_data.get('is_active', True),
                is_default=config_data.get('is_default', False),
                created_by=created_by,
                updated_by=created_by
            )
            
            db.session.add(new_config)
            db.session.commit()
            
            self.logger.info(f"Created shift configuration {new_config.shift_code} for team {team.name} by {created_by}")
            
            return {
                'success': True,
                'message': 'Shift configuration created successfully',
                'configuration': new_config.to_dict()
            }
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Error creating shift configuration: {str(e)}")
            return {
                'success': False,
                'error': 'An error occurred while creating the configuration'
            }

    def update_configuration(self, config_id: int, update_data: Dict, updated_by: str) -> Dict:
        """Update an existing shift configuration"""
        try:
            config = TeamShiftTimingConfig.query.get(config_id)
            if not config:
                return {
                    'success': False,
                    'error': 'Configuration not found'
                }
            
            # Update allowed fields
            if 'shift_name' in update_data:
                config.shift_name = update_data['shift_name'].strip()
            
            if 'start_time' in update_data:
                try:
                    config.start_time = datetime.strptime(update_data['start_time'], '%H:%M').time()
                except ValueError:
                    return {
                        'success': False,
                        'error': 'Invalid start_time format. Use HH:MM format.'
                    }
            
            if 'end_time' in update_data:
                try:
                    config.end_time = datetime.strptime(update_data['end_time'], '%H:%M').time()
                except ValueError:
                    return {
                        'success': False,
                        'error': 'Invalid end_time format. Use HH:MM format.'
                    }
            
            if 'color_code' in update_data:
                config.color_code = update_data['color_code']
            
            if 'order_index' in update_data:
                config.order_index = int(update_data['order_index'])
            
            if 'is_active' in update_data:
                config.is_active = bool(update_data['is_active'])
            
            if 'is_default' in update_data:
                config.is_default = bool(update_data['is_default'])
            
            # Overlap validation disabled for updates as well
            # This allows flexible modification of shift times
            
            config.updated_by = updated_by
            config.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            self.logger.info(f"Updated shift configuration {config.shift_code} for team {config.team_id} by {updated_by}")
            
            return {
                'success': True,
                'message': 'Shift configuration updated successfully',
                'configuration': config.to_dict()
            }
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Error updating shift configuration: {str(e)}")
            return {
                'success': False,
                'error': 'An error occurred while updating the configuration'
            }

    def delete_configuration(self, config_id: int, deleted_by: str) -> Dict:
        """Delete a shift configuration (soft delete by setting is_active=False)"""
        try:
            config = TeamShiftTimingConfig.query.get(config_id)
            if not config:
                return {
                    'success': False,
                    'error': 'Configuration not found'
                }
            
            # Soft delete by setting is_active=False
            config.is_active = False
            config.updated_by = deleted_by
            config.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            self.logger.info(f"Deleted shift configuration {config.shift_code} for team {config.team_id} by {deleted_by}")
            
            return {
                'success': True,
                'message': 'Shift configuration deleted successfully'
            }
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Error deleting shift configuration: {str(e)}")
            return {
                'success': False,
                'error': 'An error occurred while deleting the configuration'
            }

    def create_default_configurations(self, account_id: int, team_id: int, pattern: str = 'standard', created_by: str = 'system') -> Dict:
        """Create default shift configurations for a team"""
        try:
            # Validate that account and team exist
            account = Account.query.get(account_id)
            if not account:
                return {
                    'success': False,
                    'error': 'Account not found'
                }
            
            team = Team.query.filter_by(id=team_id, account_id=account_id).first()
            if not team:
                return {
                    'success': False,
                    'error': 'Team not found or does not belong to this account'
                }
            
            # Check if team already has configurations
            existing_configs = TeamShiftTimingConfig.query.filter_by(
                team_id=team_id,
                account_id=account_id,
                is_active=True
            ).count()
            
            if existing_configs > 0:
                return {
                    'success': False,
                    'error': 'Team already has shift configurations. Delete existing configurations first if you want to create defaults.'
                }
            
            # Create default configurations using model method
            created_shifts = TeamShiftTimingConfig.create_default_shifts_for_team(
                team_id=team_id,
                account_id=account_id,
                shift_pattern=pattern
            )
            
            # Update created_by for audit trail
            for shift in created_shifts:
                shift.created_by = created_by
                shift.updated_by = created_by
            
            db.session.commit()
            
            self.logger.info(f"Created {len(created_shifts)} default shift configurations for team {team.name} by {created_by}")
            
            return {
                'success': True,
                'message': f'Created {len(created_shifts)} default shift configurations successfully',
                'configurations': [shift.to_dict() for shift in created_shifts],
                'pattern': pattern
            }
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Error creating default configurations: {str(e)}")
            return {
                'success': False,
                'error': 'An error occurred while creating default configurations'
            }

    def _check_shift_overlap(self, account_id: int, team_id: int, start_time: time, end_time: time, exclude_config_id: Optional[int] = None) -> Optional[str]:
        """Check if the given shift times overlap with existing shifts - DISABLED"""
        # Overlap validation is disabled to allow overlapping shifts
        # This enables shift handovers, peak coverage, and flexible scheduling
        return None

    def _times_overlap(self, start1: time, end1: time, start2: time, end2: time) -> bool:
        """Check if two time ranges overlap"""
        # Handle overnight shifts
        def is_overnight(start, end):
            return start > end
        
        # Convert times to minutes for easier comparison
        def time_to_minutes(t):
            return t.hour * 60 + t.minute
        
        # If both are not overnight shifts
        if not is_overnight(start1, end1) and not is_overnight(start2, end2):
            return max(time_to_minutes(start1), time_to_minutes(start2)) < min(time_to_minutes(end1), time_to_minutes(end2))
        
        # If one or both are overnight shifts, we need more complex logic
        # For simplicity, we'll allow overlaps with overnight shifts for now
        # This can be enhanced based on specific business requirements
        return False

    def get_available_shift_patterns(self) -> Dict:
        """Get available shift patterns for creating defaults"""
        patterns = {
            'standard': {
                'name': 'Standard (Day/Evening/Night)',
                'description': 'Basic 3-shift pattern suitable for most operations',
                'shifts': [
                    {'code': 'D', 'name': 'Day Shift', 'time': '06:30 - 15:30'},
                    {'code': 'E', 'name': 'Evening Shift', 'time': '15:00 - 00:00'},
                    {'code': 'N', 'name': 'Night Shift', 'time': '22:00 - 07:00'},
                ]
            },
            'devops': {
                'name': 'DevOps (Onshore/Offshore)',
                'description': '24/7 coverage with onshore and offshore teams',
                'shifts': [
                    {'code': 'D', 'name': 'Day Shift (Onshore)', 'time': '06:30 - 15:30'},
                    {'code': 'N', 'name': 'Night Shift (Offshore)', 'time': '22:00 - 07:00'},
                ]
            },
            'extended': {
                'name': 'Extended (5 Shifts)',
                'description': 'Comprehensive shift pattern with maximum flexibility',
                'shifts': [
                    {'code': 'D', 'name': 'Day Shift', 'time': '06:30 - 15:30'},
                    {'code': 'E', 'name': 'Evening Shift', 'time': '15:00 - 00:00'},
                    {'code': 'N', 'name': 'Night Shift', 'time': '22:00 - 07:00'},
                    {'code': 'LE', 'name': 'Late Evening Shift', 'time': '18:00 - 03:00'},
                    {'code': 'G', 'name': 'General Shift', 'time': '10:00 - 19:00'},
                ]
            }
        }
        
        return {
            'success': True,
            'patterns': patterns
        }