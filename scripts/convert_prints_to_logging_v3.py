#!/usr/bin/env python3
"""
Script to convert remaining print statements to logger calls.
Version 3.0 - Handles flush=True, variable prints, and separator patterns.
"""

import re
import sys
from pathlib import Path

def convert_file(filepath):
    """Convert print statements to logger calls in a single file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Check if logging is already imported
    has_logging_import = 'import logging' in content
    has_logger = 'logger = logging.getLogger' in content
    
    # Pattern replacements - from specific to general
    replacements = [
        # Handle prints with flush=True
        (r'print\(f"([^"]*)", flush=True\)', r'logger.debug(f"\1")'),
        (r'print\("([^"]*)", flush=True\)', r'logger.debug("\1")'),
        
        # Handle separator patterns like print("="*50)
        (r'print\("="\*\d+\)', r'logger.debug("=" * 50)'),
        
        # Handle variable prints like print(msg)
        (r'(\s+)print\(msg\)', r'\1logger.debug(msg)'),
        
        # Handle prints with \n at start
        (r'print\(f"\\n([^"]*)"[^)]*\)', r'logger.debug(f"\1")'),
        
        # Error indicators (various emojis)
        (r'print\(f"🚨([^"]*)"\)', r'logger.warning(f"🚨\1")'),
        (r'print\("🚨([^"]*)"\)', r'logger.warning("🚨\1")'),
        
        # Debug indicators
        (r'print\(f"🔧([^"]*)"\)', r'logger.debug(f"🔧\1")'),
        (r'print\("🔧([^"]*)"\)', r'logger.debug("🔧\1")'),
        (r'print\(f"🔍([^"]*)"\)', r'logger.debug(f"🔍\1")'),
        (r'print\("🔍([^"]*)"\)', r'logger.debug("🔍\1")'),
        (r'print\(f"🔄([^"]*)"\)', r'logger.debug(f"🔄\1")'),
        (r'print\("🔄([^"]*)"\)', r'logger.debug("🔄\1")'),
        
        # Debug prefixed prints
        (r'print\(f"\[DEBUG[^\]]*\]([^"]*)"\)', r'logger.debug(f"[DEBUG]\1")'),
        (r'print\("\[DEBUG[^\]]*\]([^"]*)"\)', r'logger.debug("[DEBUG]\1")'),
        (r'print\("DEBUG:([^"]*)"\)', r'logger.debug("DEBUG:\1")'),
        
        # Labeled prints like [TEAM_API] 
        (r'print\(f"\[([A-Z_]+)\]([^"]*)"\)', r'logger.debug(f"[\1]\2")'),
        (r'print\("\[([A-Z_]+)\]([^"]*)"\)', r'logger.debug("[\1]\2")'),
        
        # Handle multiline print statements - simplified pattern
        (r'print\(\s*\n\s*f"([^"]*)"\s*\n\s*\)', r'logger.debug(f"\1")'),
        
        # Generic f-string prints
        (r'print\(f"([^"]*)"\)', r'logger.debug(f"\1")'),
        
        # Generic regular string prints
        (r'print\("([^"]*)"\)', r'logger.debug("\1")'),
        
        # Handle single-quoted strings
        (r"print\(f'([^']*)'\)", r"logger.debug(f'\1')"),
        (r"print\('([^']*)'\)", r"logger.debug('\1')"),
    ]
    
    for pattern, replacement in replacements:
        content = re.sub(pattern, replacement, content)
    
    # Check if we need to add logging imports
    if content != original_content:
        if 'logger.' in content and not has_logging_import:
            # Add logging import after other imports
            import_section_end = 0
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if line.startswith('import ') or line.startswith('from '):
                    import_section_end = i
            
            # Insert logging import after last import
            if import_section_end > 0:
                lines.insert(import_section_end + 1, 'import logging')
                content = '\n'.join(lines)
            else:
                content = 'import logging\n' + content
        
        if 'logger.' in content and not has_logger:
            # Add logger initialization after imports
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if line.startswith('import logging'):
                    lines.insert(i + 1, 'logger = logging.getLogger(__name__)')
                    break
            content = '\n'.join(lines)
    
    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Count changes
        old_count = len(re.findall(r'print\(', original_content))
        new_count = len(re.findall(r'print\(', content))
        converted = old_count - new_count
        
        return converted
    
    return 0

def main():
    # Route files to convert - all active route files
    route_files = [
        'routes/debug_form.py',
        'routes/reports.py',
        'routes/auth.py',
        'routes/user_profile.py',
        'routes/user_management.py',
        'routes/team_simple.py',
        'routes/shift_swap_leave.py',
        'routes/admin_secrets.py',
        'routes/team.py',
        'routes/misc.py',
        'routes/keypoints.py',
        'routes/checkin.py',
        'routes/roster_upload.py',
        'routes/handover_simple.py',
        'routes/dashboard_temp.py',
        'routes/auth_debug.py',
        'routes/handover.py',
        'routes/dashboard.py',
        'routes/sso_auth.py',
        'routes/vendor_details.py',
        'routes/handover_enhanced_routes.py',
        'routes/incident_assignment.py',
        'routes/team_roster.py',
        'routes/assignment_response.py',
        'routes/admin.py',
        'routes/roster.py',
        'routes/escalation_matrix.py',
        'routes/shift_allowance.py',
        'routes/email_config_routes.py',
        'routes/keypoints_enhanced.py',
        'routes/team_utils.py',
        'routes/handover_management.py',
        'routes/shift_config.py',
        'routes/onboarding_new.py',
        'routes/sso_config.py',
        'routes/test_routes.py',
        'routes/kb_details.py',
        'routes/logs.py',
        'routes/onboarding.py',
        'routes/config.py',
        'routes/ctask_assignment.py',
        'routes/admin_uns_email.py',
        'routes/application_details.py',
        'routes/admin_linking.py',
    ]
    
    total_converted = 0
    for filepath in route_files:
        if Path(filepath).exists():
            converted = convert_file(filepath)
            if converted > 0:
                print(f"Converted {converted} print statements in {filepath}")
                total_converted += converted
    
    print(f"\nTotal converted: {total_converted} print statements")

if __name__ == '__main__':
    main()

