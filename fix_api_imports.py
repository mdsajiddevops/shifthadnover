#!/usr/bin/env python3
"""
Fix the import issue in the shift API
"""
import re

# Read the current file
with open('/app/routes/shift_swap_leave.py', 'r') as f:
    content = f.read()

# Fix the imports in the get_user_shift_for_date function
# Replace the wrong imports with correct ones
old_imports = """        from datetime import datetime
        from models.shift_roster import ShiftRoster
        from models.team_member import TeamMember"""

new_imports = """        from datetime import datetime
        from models.models import ShiftRoster, TeamMember"""

content = content.replace(old_imports, new_imports)

# Write the fixed content back
with open('/app/routes/shift_swap_leave.py', 'w') as f:
    f.write(content)

print("✅ Fixed import issue in get_user_shift_for_date function!")