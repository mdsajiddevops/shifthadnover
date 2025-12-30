#!/usr/bin/env python3
"""
Script to add logging imports to route files that have logger calls but no import.
"""
import re
import os

def add_logging_import(filepath):
    """Add logging import to a file if it has logger calls but no import."""
    print(f"Checking: {filepath}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if file has logger calls
    has_logger_calls = 'logger.' in content
    
    # Check if already has logging import
    has_logging_import = 'import logging' in content
    has_logger_definition = 'logger = logging.getLogger' in content
    
    if not has_logger_calls:
        print("  - No logger calls found, skipping")
        return
    
    if has_logging_import and has_logger_definition:
        print("  - Already has logging setup")
        return
    
    # Find the last import line to insert after
    lines = content.split('\n')
    last_import_idx = 0
    blueprint_line_idx = 0
    
    for i, line in enumerate(lines):
        if line.startswith('import ') or line.startswith('from '):
            last_import_idx = i
        if '_bp = Blueprint(' in line or '_bp=Blueprint(' in line:
            blueprint_line_idx = i
            break
    
    # Insert logging import and logger definition before blueprint
    if not has_logging_import:
        lines.insert(last_import_idx + 1, 'import logging')
        last_import_idx += 1
        blueprint_line_idx += 1
    
    if not has_logger_definition:
        # Insert logger definition right before blueprint definition
        lines.insert(blueprint_line_idx, '')
        lines.insert(blueprint_line_idx + 1, '# Module logger')
        lines.insert(blueprint_line_idx + 2, 'logger = logging.getLogger(__name__)')
    
    # Write back
    new_content = '\n'.join(lines)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"  - Added logging setup")

def main():
    routes_dir = 'routes'
    
    route_files = [
        'handover.py', 'dashboard.py', 'reports.py', 'keypoints.py',
        'auth.py', 'roster_upload.py', 'team_roster.py', 'team_simple.py',
        'user_management.py', 'admin.py', 'admin_secrets.py', 'checkin.py',
        'user_profile.py', 'incident_assignment.py', 'misc.py', 'roster.py',
        'escalation_matrix.py', 'vendor_details.py', 'assignment_response.py',
        'shift_swap_leave.py', 'email_config_routes.py', 'shift_config.py',
        'sso_auth.py', 'sso_config.py', 'admin_linking.py', 'onboarding.py',
        'config.py', 'ctask_assignment.py', 'logs.py', 'test_routes.py',
        'admin_uns_email.py', 'debug_form.py', 'handover_enhanced_routes.py',
        'team_utils.py', 'shift_allowance.py',
    ]
    
    for filename in route_files:
        filepath = os.path.join(routes_dir, filename)
        if os.path.exists(filepath):
            add_logging_import(filepath)

if __name__ == '__main__':
    main()

