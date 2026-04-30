#!/usr/bin/env python3
"""
Script to convert print statements to logger calls in models and services.
"""

import re
from pathlib import Path

def convert_file(filepath):
    """Convert print statements to logger calls in a single file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Check if logging is already imported
    has_logging_import = 'import logging' in content
    has_logger = 'logger = logging.getLogger' in content
    
    # Pattern replacements
    replacements = [
        # Handle prints with flush=True
        (r'print\(f"([^"]*)", flush=True\)', r'logger.debug(f"\1")'),
        (r'print\("([^"]*)", flush=True\)', r'logger.debug("\1")'),
        
        # Handle separator patterns like print("="*50)
        (r'print\("="\*\d+\)', r'logger.debug("=" * 50)'),
        (r'print\("-"\*\d+\)', r'logger.debug("-" * 50)'),
        
        # Handle variable prints like print(msg)
        (r'(\s+)print\(msg\)', r'\1logger.debug(msg)'),
        (r'(\s+)print\(e\)', r'\1logger.error(e)'),
        
        # Error indicators (various emojis)
        (r'print\(f"🚨([^"]*)"\)', r'logger.warning(f"🚨\1")'),
        (r'print\("🚨([^"]*)"\)', r'logger.warning("🚨\1")'),
        (r'print\(f"❌([^"]*)"\)', r'logger.error(f"❌\1")'),
        (r'print\("❌([^"]*)"\)', r'logger.error("❌\1")'),
        
        # Success indicators
        (r'print\(f"✅([^"]*)"\)', r'logger.info(f"✅\1")'),
        (r'print\("✅([^"]*)"\)', r'logger.info("✅\1")'),
        (r'print\(f"✓([^"]*)"\)', r'logger.info(f"✓\1")'),
        (r'print\("✓([^"]*)"\)', r'logger.info("✓\1")'),
        
        # Warning indicators
        (r'print\(f"⚠️([^"]*)"\)', r'logger.warning(f"⚠️\1")'),
        (r'print\("⚠️([^"]*)"\)', r'logger.warning("⚠️\1")'),
        
        # Debug indicators
        (r'print\(f"🔧([^"]*)"\)', r'logger.debug(f"🔧\1")'),
        (r'print\("🔧([^"]*)"\)', r'logger.debug("🔧\1")'),
        (r'print\(f"🔍([^"]*)"\)', r'logger.debug(f"🔍\1")'),
        (r'print\("🔍([^"]*)"\)', r'logger.debug("🔍\1")'),
        (r'print\(f"🔄([^"]*)"\)', r'logger.debug(f"🔄\1")'),
        (r'print\("🔄([^"]*)"\)', r'logger.debug("🔄\1")'),
        (r'print\(f"📧([^"]*)"\)', r'logger.debug(f"📧\1")'),
        (r'print\("📧([^"]*)"\)', r'logger.debug("📧\1")'),
        (r'print\(f"📚([^"]*)"\)', r'logger.debug(f"📚\1")'),
        (r'print\("📚([^"]*)"\)', r'logger.debug("📚\1")'),
        (r'print\(f"📝([^"]*)"\)', r'logger.debug(f"📝\1")'),
        (r'print\("📝([^"]*)"\)', r'logger.debug("📝\1")'),
        (r'print\(f"📨([^"]*)"\)', r'logger.debug(f"📨\1")'),
        (r'print\("📨([^"]*)"\)', r'logger.debug("📨\1")'),
        (r'print\(f"📩([^"]*)"\)', r'logger.debug(f"📩\1")'),
        (r'print\("📩([^"]*)"\)', r'logger.debug("📩\1")'),
        
        # Handle prints with \n at start
        (r'print\(f"\\n([^"]*)"\)', r'logger.debug(f"\1")'),
        (r'print\("\\n([^"]*)"\)', r'logger.debug("\1")'),
        
        # Handle indented lines
        (r'print\(f"   ([^"]*)"\)', r'logger.debug(f"   \1")'),
        (r'print\("   ([^"]*)"\)', r'logger.debug("   \1")'),
        
        # Debug prefixed prints
        (r'print\(f"\[DEBUG[^\]]*\]([^"]*)"\)', r'logger.debug(f"[DEBUG]\1")'),
        (r'print\("\[DEBUG[^\]]*\]([^"]*)"\)', r'logger.debug("[DEBUG]\1")'),
        
        # Labeled prints
        (r'print\(f"\[([A-Z_]+)\]([^"]*)"\)', r'logger.debug(f"[\1]\2")'),
        (r'print\("\[([A-Z_]+)\]([^"]*)"\)', r'logger.debug("[\1]\2")'),
        
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
    # Files to convert
    files = [
        'models/team_roster_models.py',
        'models/sso_config.py',
        'services/email_service.py',
        'services/flask_uns_email.py',
        'services/multi_team_service.py',
        'services/email_config_service.py',
        'services/servicenow_service.py',
        'services/shift_config_service.py',
        'services/console_service.py',
    ]
    
    total_converted = 0
    for filepath in files:
        if Path(filepath).exists():
            converted = convert_file(filepath)
            if converted > 0:
                print(f"Converted {converted} print statements in {filepath}")
                total_converted += converted
    
    print(f"\nTotal converted: {total_converted} print statements")

if __name__ == '__main__':
    main()









