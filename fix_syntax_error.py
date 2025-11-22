#!/usr/bin/env python3
"""
Fix the syntax error in shift_swap_leave.py routes file
"""
import sys
import os

# Add the current directory to Python path
sys.path.append('/app')

def fix_syntax_error():
    """Fix the syntax error in the routes file"""
    
    print("🔧 FIXING SYNTAX ERROR IN ROUTES FILE")
    print("=" * 60)
    
    try:
        route_file = '/app/routes/shift_swap_leave.py'
        
        with open(route_file, 'r') as f:
            content = f.read()
        
        # Find and fix the problematic line
        # Look for the broken line with line break
        broken_pattern = "'user_requests': shift_swap_leave_service.get_user_requests\n(current_user.id),"
        fixed_pattern = "'user_requests': shift_swap_leave_service.get_user_requests(current_user.id),"
        
        if broken_pattern in content:
            content = content.replace(broken_pattern, fixed_pattern)
            print("✅ Fixed broken line with method call")
        
        # Also check for other potential syntax issues
        lines = content.split('\n')
        fixed_lines = []
        
        for i, line in enumerate(lines):
            # Fix any hanging method calls
            if "'user_requests': shift_swap_leave_service.get_user_requests" in line and not line.strip().endswith(','):
                if i + 1 < len(lines) and lines[i + 1].strip().startswith('(current_user.id)'):
                    # Merge the lines
                    merged_line = line.replace('get_user_requests', 'get_user_requests(current_user.id),')
                    fixed_lines.append(merged_line)
                    # Skip the next line as we merged it
                    if i + 1 < len(lines):
                        i += 1
                        continue
                else:
                    fixed_lines.append(line)
            elif line.strip() == "(current_user.id)," and i > 0 and "'user_requests':" in lines[i-1]:
                # Skip this line as it should be merged with previous
                continue
            else:
                fixed_lines.append(line)
        
        content = '\n'.join(fixed_lines)
        
        with open(route_file, 'w') as f:
            f.write(content)
        
        print("✅ Fixed syntax error in routes file")
        print("  • Merged broken method call lines")
        print("  • Ensured proper Python syntax")
        
    except Exception as e:
        print(f"❌ Error fixing syntax: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    fix_syntax_error()