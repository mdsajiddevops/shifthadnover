#!/usr/bin/env python3
"""
Script to convert print statements to logger calls in Python files.
Version 2.0 - Handles more patterns and edge cases.
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
        # Error indicators
        (r'print\(f?"🚨([^"]*)"\.format\(([^)]*)\)\)', r'logger.warning(f"🚨\1".format(\2))'),
        (r'print\(f"🚨([^"]*)"\)', r'logger.warning(f"🚨\1")'),
        (r'print\("🚨([^"]*)"\)', r'logger.warning("🚨\1")'),
        
        # Debug indicators (wrench emoji)
        (r'print\(f"🔧([^"]*)"\)', r'logger.debug(f"🔧\1")'),
        (r'print\("🔧([^"]*)"\)', r'logger.debug("🔧\1")'),
        
        # Debug/search indicators
        (r'print\(f"🔍([^"]*)"\)', r'logger.debug(f"🔍\1")'),
        (r'print\("🔍([^"]*)"\)', r'logger.debug("🔍\1")'),
        
        # Bug indicators
        (r'print\(f"🐛([^"]*)"\)', r'logger.debug(f"🐛\1")'),
        (r'print\("🐛([^"]*)"\)', r'logger.debug("🐛\1")'),
        
        # Success indicators
        (r'print\(f"✅([^"]*)"\)', r'logger.info(f"✅\1")'),
        (r'print\("✅([^"]*)"\)', r'logger.info("✅\1")'),
        
        # Warning indicators
        (r'print\(f"⚠️([^"]*)"\)', r'logger.warning(f"⚠️\1")'),
        (r'print\("⚠️([^"]*)"\)', r'logger.warning("⚠️\1")'),
        
        # Info indicators (book emoji)
        (r'print\(f"📚([^"]*)"\)', r'logger.debug(f"📚\1")'),
        (r'print\("📚([^"]*)"\)', r'logger.debug("📚\1")'),
        
        # Handle newlines at start (common in debug prints)
        (r'print\(f"\\n([^"]*)"\)', r'logger.debug(f"\1")'),
        (r'print\("\\n([^"]*)"\)', r'logger.debug("\1")'),
        
        # Handle prints with indentation markers
        (r'print\(f"   ([^"]*)"\)', r'logger.debug(f"   \1")'),
        (r'print\("   ([^"]*)"\)', r'logger.debug("   \1")'),
        
        # Generic f-string prints with common patterns
        (r'print\(f"DEBUG([^"]*)"\)', r'logger.debug(f"DEBUG\1")'),
        (r'print\(f"Error([^"]*)"\)', r'logger.error(f"Error\1")'),
        (r'print\(f"Warning([^"]*)"\)', r'logger.warning(f"Warning\1")'),
        
        # Catch remaining generic f-string prints
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
    # Route files to convert
    route_files = [
        'routes/handover.py',
        'routes/reports.py',
        'routes/team.py',
        'routes/misc.py',
        'routes/keypoints.py',
        'routes/checkin.py',
        'routes/roster_upload.py',
        'routes/debug_form.py',
        'routes/handover_simple.py',
        'routes/dashboard_temp.py',
        'routes/auth_debug.py',
    ]
    
    total_converted = 0
    for filepath in route_files:
        if Path(filepath).exists():
            converted = convert_file(filepath)
            if converted > 0:
                print(f"Converted {converted} print statements in {filepath}")
                total_converted += converted
        else:
            print(f"File not found: {filepath}")
    
    print(f"\nTotal converted: {total_converted} print statements")

if __name__ == '__main__':
    main()




