#!/usr/bin/env python3
"""
Script to convert print statements to proper logging in route files.
Phase 1 Performance Improvement - Zero impact on functionality.
"""
import re
import os

def convert_file(filepath):
    """Convert print statements to logging in a single file."""
    print(f"\n{'='*60}")
    print(f"Processing: {filepath}")
    print(f"{'='*60}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Count original print statements
    original_count = len(re.findall(r'print\(f?"', content))
    print(f"Found {original_count} print statements")
    
    if original_count == 0:
        print("No print statements to convert")
        return
    
    # Replace patterns - preserve functionality, just change output method
    replacements = [
        # Tagged debug messages - ALL CAPS
        (r'print\(f"\[NEW_SHIFT\]', 'logger.debug(f"[NEW_SHIFT]'),
        (r'print\(f"\[SHIFT_TYPE\]', 'logger.debug(f"[SHIFT_TYPE]'),
        (r'print\(f"\[HANDOVER\]', 'logger.debug(f"[HANDOVER]'),
        (r'print\(f"\[DEBUG\]', 'logger.debug(f"[DEBUG]'),
        (r'print\(f"\[INCIDENT\]', 'logger.debug(f"[INCIDENT]'),
        (r'print\(f"\[KEY_POINT\]', 'logger.debug(f"[KEY_POINT]'),
        (r'print\(f"\[KEYPOINT\]', 'logger.debug(f"[KEYPOINT]'),
        (r'print\(f"\[CHANGE_INFO\]', 'logger.debug(f"[CHANGE_INFO]'),
        (r'print\(f"\[KB_UPDATE\]', 'logger.debug(f"[KB_UPDATE]'),
        (r'print\(f"\[KB\]', 'logger.debug(f"[KB]'),
        (r'print\(f"\[ENGINEER\]', 'logger.debug(f"[ENGINEER]'),
        (r'print\(f"\[FORM\]', 'logger.debug(f"[FORM]'),
        (r'print\(f"\[EDIT\]', 'logger.debug(f"[EDIT]'),
        (r'print\(f"\[SAVE\]', 'logger.debug(f"[SAVE]'),
        (r'print\(f"\[LOAD\]', 'logger.debug(f"[LOAD]'),
        (r'print\(f"\[TEAM\]', 'logger.debug(f"[TEAM]'),
        (r'print\(f"\[ROSTER\]', 'logger.debug(f"[ROSTER]'),
        (r'print\(f"\[API\]', 'logger.debug(f"[API]'),
        (r'print\(f"\[DRAFT\]', 'logger.debug(f"[DRAFT]'),
        (r'print\(f"\[FILTER\]', 'logger.debug(f"[FILTER]'),
        (r'print\(f"\[QUERY\]', 'logger.debug(f"[QUERY]'),
        (r'print\(f"\[USER\]', 'logger.debug(f"[USER]'),
        (r'print\(f"\[PERMISSION\]', 'logger.debug(f"[PERMISSION]'),
        (r'print\(f"\[ACCESS\]', 'logger.debug(f"[ACCESS]'),
        (r'print\(f"\[SESSION\]', 'logger.debug(f"[SESSION]'),
        (r'print\(f"\[CONTEXT\]', 'logger.debug(f"[CONTEXT]'),
        (r'print\(f"\[DASHBOARD\]', 'logger.debug(f"[DASHBOARD]'),
        (r'print\(f"\[REPORT\]', 'logger.debug(f"[REPORT]'),
        (r'print\(f"\[REPORTS\]', 'logger.debug(f"[REPORTS]'),
        (r'print\(f"\[EXPORT\]', 'logger.debug(f"[EXPORT]'),
        (r'print\(f"\[AUTH\]', 'logger.debug(f"[AUTH]'),
        (r'print\(f"\[LOGIN\]', 'logger.info(f"[LOGIN]'),
        (r'print\(f"\[LOGOUT\]', 'logger.info(f"[LOGOUT]'),
        (r'print\(f"\[PROFILE\]', 'logger.debug(f"[PROFILE]'),
        (r'print\(f"\[ADMIN\]', 'logger.debug(f"[ADMIN]'),
        (r'print\(f"\[CONFIG\]', 'logger.debug(f"[CONFIG]'),
        (r'print\(f"\[SSO\]', 'logger.info(f"[SSO]'),
        (r'print\(f"\[LINKING\]', 'logger.debug(f"[LINKING]'),
        (r'print\(f"\[ROSTER_UPLOAD\]', 'logger.debug(f"[ROSTER_UPLOAD]'),
        (r'print\(f"\[ESCALATION\]', 'logger.debug(f"[ESCALATION]'),
        (r'print\(f"\[VENDOR\]', 'logger.debug(f"[VENDOR]'),
        (r'print\(f"\[SWAP\]', 'logger.debug(f"[SWAP]'),
        (r'print\(f"\[LEAVE\]', 'logger.debug(f"[LEAVE]'),
        (r'print\(f"\[CHECKIN\]', 'logger.debug(f"[CHECKIN]'),
        (r'print\(f"\[NOTIFICATION\]', 'logger.debug(f"[NOTIFICATION]'),
        (r'print\(f"\[ASSIGNMENT\]', 'logger.debug(f"[ASSIGNMENT]'),
        (r'print\(f"\[ONBOARDING\]', 'logger.debug(f"[ONBOARDING]'),
        (r'print\(f"\[SECRETS\]', 'logger.debug(f"[SECRETS]'),
        (r'print\(f"\[EMAIL_CONFIG\]', 'logger.debug(f"[EMAIL_CONFIG]'),
        (r'print\(f"\[SHIFT_CONFIG\]', 'logger.debug(f"[SHIFT_CONFIG]'),
        (r'print\(f"\[SERVICE\]', 'logger.debug(f"[SERVICE]'),
        (r'print\(f"\[SERVICENOW\]', 'logger.debug(f"[SERVICENOW]'),
        (r'print\(f"\[CTASK\]', 'logger.debug(f"[CTASK]'),
        (r'print\(f"\[SYNC\]', 'logger.debug(f"[SYNC]'),
        (r'print\(f"\[DB\]', 'logger.debug(f"[DB]'),
        (r'print\(f"\[VALIDATE\]', 'logger.debug(f"[VALIDATE]'),
        (r'print\(f"\[VALIDATION\]', 'logger.debug(f"[VALIDATION]'),
        
        # Tagged messages - Mixed case and specific patterns found in codebase
        (r'print\(f"\[HANDOVER NOTIFICATION\]', 'logger.debug(f"[HANDOVER NOTIFICATION]'),
        (r'print\(f"\[SHIFT FIX\]', 'logger.debug(f"[SHIFT FIX]'),
        (r'print\(f"\[SHIFT FIX API\]', 'logger.debug(f"[SHIFT FIX API]'),
        (r'print\(f"\[GET_ENGINEERS\]', 'logger.debug(f"[GET_ENGINEERS]'),
        (r'print\(f"\[HANDOVER FIX\]', 'logger.debug(f"[HANDOVER FIX]'),
        (r'print\(f"\[API_TEAM_MEMBERS\]', 'logger.debug(f"[API_TEAM_MEMBERS]'),
        (r'print\(f"\[EDIT_HANDOVER\]', 'logger.debug(f"[EDIT_HANDOVER]'),
        (r'print\(f"\[HANDOVER_FORM\]', 'logger.debug(f"[HANDOVER_FORM]'),
        (r'print\(f"\[KEY_POINTS\]', 'logger.debug(f"[KEY_POINTS]'),
        (r'print\(f"\[KEYPOINTS\]', 'logger.debug(f"[KEYPOINTS]'),
        (r'print\(f"\[ENGINEERS\]', 'logger.debug(f"[ENGINEERS]'),
        (r'print\(f"\[INCIDENTS\]', 'logger.debug(f"[INCIDENTS]'),
        (r'print\(f"\[CHANGE_INFOS\]', 'logger.debug(f"[CHANGE_INFOS]'),
        (r'print\(f"\[KB_UPDATES\]', 'logger.debug(f"[KB_UPDATES]'),
        (r'print\(f"\[TEAM_ACCESS\]', 'logger.debug(f"[TEAM_ACCESS]'),
        (r'print\(f"\[MULTI_TEAM\]', 'logger.debug(f"[MULTI_TEAM]'),
        (r'print\(f"\[SESSION_FIX\]', 'logger.debug(f"[SESSION_FIX]'),
        (r'print\(f"\[DEDUP\]', 'logger.debug(f"[DEDUP]'),
        (r'print\(f"\[CREATE_SHIFT\]', 'logger.debug(f"[CREATE_SHIFT]'),
        (r'print\(f"\[SUBMIT_SHIFT\]', 'logger.info(f"[SUBMIT_SHIFT]'),
        (r'print\(f"\[EMAIL_SEND\]', 'logger.info(f"[EMAIL_SEND]'),
        (r'print\(f"\[FORM_DATA\]', 'logger.debug(f"[FORM_DATA]'),
        (r'print\(f"\[SAVE_DRAFT\]', 'logger.debug(f"[SAVE_DRAFT]'),
        (r'print\(f"\[DELETE\]', 'logger.debug(f"[DELETE]'),
        (r'print\(f"\[CLEANUP\]', 'logger.debug(f"[CLEANUP]'),
        (r'print\(f"\[COPY\]', 'logger.debug(f"[COPY]'),
        (r'print\(f"\[DUPLICATE\]', 'logger.debug(f"[DUPLICATE]'),
        (r'print\(f"\[STATUS\]', 'logger.debug(f"[STATUS]'),
        (r'print\(f"\[UPDATE\]', 'logger.debug(f"[UPDATE]'),
        (r'print\(f"\[FETCH\]', 'logger.debug(f"[FETCH]'),
        (r'print\(f"\[RENDER\]', 'logger.debug(f"[RENDER]'),
        
        # Emoji patterns found in codebase (must come before generic patterns)
        (r'print\(f"[^"]*\\ud83d', 'logger.debug(f"'),  # Any emoji starting patterns
        
        # Info level messages
        (r'print\(f"\[INFO\]', 'logger.info(f"[INFO]'),
        (r'print\(f"\[EMAIL\]', 'logger.info(f"[EMAIL]'),
        (r'print\(f"\[SUBMIT\]', 'logger.info(f"[SUBMIT]'),
        
        # Warning level messages  
        (r'print\(f"\[WARNING\]', 'logger.warning(f"[WARNING]'),
        (r'print\(f"\[WARN\]', 'logger.warning(f"[WARN]'),
        
        # Error level messages
        (r'print\(f"\[ERROR\]', 'logger.error(f"[ERROR]'),
        
        # Debug headers with ===
        (r'print\(f"===', 'logger.debug(f"==='),
        (r'print\("===', 'logger.debug("==='),
        
        # Emoji indicators
        (r'print\(f"✅', 'logger.info(f"✅'),
        (r'print\(f"❌', 'logger.error(f"❌'),
        (r'print\(f"⚠️', 'logger.warning(f"⚠️'),
        (r'print\(f"🔍', 'logger.debug(f"🔍'),
        (r'print\(f"📧', 'logger.info(f"📧'),
        (r'print\(f"🚀', 'logger.info(f"🚀'),
        
        # Generic remaining patterns - convert to debug
        (r'print\(f"  -', 'logger.debug(f"  -'),
        (r'print\(f"    ', 'logger.debug(f"    '),
        (r'print\(f"Processing', 'logger.debug(f"Processing'),
        (r'print\(f"Loaded', 'logger.debug(f"Loaded'),
        (r'print\(f"Found', 'logger.debug(f"Found'),
        (r'print\(f"Fetching', 'logger.debug(f"Fetching'),
        (r'print\(f"Creating', 'logger.debug(f"Creating'),
        (r'print\(f"Updated', 'logger.debug(f"Updated'),
        (r'print\(f"Saving', 'logger.debug(f"Saving'),
        (r'print\(f"Deleting', 'logger.debug(f"Deleting'),
        
        # More patterns for remaining statements
        (r'print\(f"Setting', 'logger.debug(f"Setting'),
        (r'print\(f"Getting', 'logger.debug(f"Getting'),
        (r'print\(f"Checking', 'logger.debug(f"Checking'),
        (r'print\(f"Adding', 'logger.debug(f"Adding'),
        (r'print\(f"Removing', 'logger.debug(f"Removing'),
        (r'print\(f"Loading', 'logger.debug(f"Loading'),
        (r'print\(f"Parsing', 'logger.debug(f"Parsing'),
        (r'print\(f"Generating', 'logger.debug(f"Generating'),
        (r'print\(f"Sending', 'logger.info(f"Sending'),
        (r'print\(f"Received', 'logger.debug(f"Received'),
        (r'print\(f"Returned', 'logger.debug(f"Returned'),
        (r'print\(f"Result', 'logger.debug(f"Result'),
        (r'print\(f"Response', 'logger.debug(f"Response'),
        (r'print\(f"Request', 'logger.debug(f"Request'),
        (r'print\(f"Data', 'logger.debug(f"Data'),
        (r'print\(f"Value', 'logger.debug(f"Value'),
        (r'print\(f"Key', 'logger.debug(f"Key'),
        (r'print\(f"User', 'logger.debug(f"User'),
        (r'print\(f"Team', 'logger.debug(f"Team'),
        (r'print\(f"Account', 'logger.debug(f"Account'),
        (r'print\(f"Shift', 'logger.debug(f"Shift'),
        (r'print\(f"Engineer', 'logger.debug(f"Engineer'),
        (r'print\(f"Current', 'logger.debug(f"Current'),
        (r'print\(f"Next', 'logger.debug(f"Next'),
        (r'print\(f"Selected', 'logger.debug(f"Selected'),
        (r'print\(f"Available', 'logger.debug(f"Available'),
        (r'print\(f"Total', 'logger.debug(f"Total'),
        (r'print\(f"Count', 'logger.debug(f"Count'),
        (r'print\(f"Index', 'logger.debug(f"Index'),
        (r'print\(f"ID', 'logger.debug(f"ID'),
        (r'print\(f"Status', 'logger.debug(f"Status'),
        (r'print\(f"Type', 'logger.debug(f"Type'),
        (r'print\(f"Name', 'logger.debug(f"Name'),
        (r'print\(f"Email', 'logger.debug(f"Email'),
        (r'print\(f"Date', 'logger.debug(f"Date'),
        (r'print\(f"Time', 'logger.debug(f"Time'),
        (r'print\(f"Query', 'logger.debug(f"Query'),
        (r'print\(f"Filter', 'logger.debug(f"Filter'),
        (r'print\(f"Sort', 'logger.debug(f"Sort'),
        (r'print\(f"Page', 'logger.debug(f"Page'),
        (r'print\(f"Error', 'logger.error(f"Error'),
        (r'print\(f"Failed', 'logger.error(f"Failed'),
        (r'print\(f"Success', 'logger.info(f"Success'),
        (r'print\(f"Complete', 'logger.info(f"Complete'),
        (r'print\(f"Done', 'logger.info(f"Done'),
        (r'print\(f"Start', 'logger.debug(f"Start'),
        (r'print\(f"End', 'logger.debug(f"End'),
        (r'print\(f"Begin', 'logger.debug(f"Begin'),
        (r'print\(f"Finish', 'logger.info(f"Finish'),
        (r'print\(f"Init', 'logger.debug(f"Init'),
        (r'print\(f"Initialize', 'logger.debug(f"Initialize'),
        (r'print\(f"Initialized', 'logger.debug(f"Initialized'),
        (r'print\(f"Configure', 'logger.debug(f"Configure'),
        (r'print\(f"Configured', 'logger.debug(f"Configured'),
        (r'print\(f"Validate', 'logger.debug(f"Validate'),
        (r'print\(f"Validated', 'logger.debug(f"Validated'),
        (r'print\(f"Valid', 'logger.debug(f"Valid'),
        (r'print\(f"Invalid', 'logger.warning(f"Invalid'),
        (r'print\(f"Missing', 'logger.warning(f"Missing'),
        (r'print\(f"Not found', 'logger.warning(f"Not found'),
        (r'print\(f"Already', 'logger.debug(f"Already'),
        (r'print\(f"Skip', 'logger.debug(f"Skip'),
        (r'print\(f"Skipping', 'logger.debug(f"Skipping'),
        (r'print\(f"Include', 'logger.debug(f"Include'),
        (r'print\(f"Exclude', 'logger.debug(f"Exclude'),
        (r'print\(f"Matched', 'logger.debug(f"Matched'),
        (r'print\(f"Match', 'logger.debug(f"Match'),
        (r'print\(f"No ', 'logger.debug(f"No '),
        (r'print\(f"Final', 'logger.debug(f"Final'),
        (r'print\(f"Raw', 'logger.debug(f"Raw'),
        (r'print\(f"Parsed', 'logger.debug(f"Parsed'),
        (r'print\(f"Debug', 'logger.debug(f"Debug'),
        (r'print\(f"Profile', 'logger.debug(f"Profile'),
        (r'print\(f"Form', 'logger.debug(f"Form'),
        (r'print\(f"Password', 'logger.debug(f"Password'),
        (r'print\(f"Update', 'logger.debug(f"Update'),
        (r'print\(f"Existing', 'logger.debug(f"Existing'),
        (r'print\(f"New', 'logger.debug(f"New'),
        (r'print\(f"Old', 'logger.debug(f"Old'),
        (r'print\(f"Commit', 'logger.debug(f"Commit'),
        (r'print\(f"Rollback', 'logger.warning(f"Rollback'),
        (r'print\(f"Exception', 'logger.error(f"Exception'),
        (r'print\(f"Traceback', 'logger.error(f"Traceback'),
        (r'print\(f"Warning', 'logger.warning(f"Warning'),
        (r'print\(f"Info', 'logger.info(f"Info'),
        (r'print\(f"Note', 'logger.debug(f"Note'),
        (r'print\(f"Applied', 'logger.debug(f"Applied'),
        (r'print\(f"Applying', 'logger.debug(f"Applying'),
        (r'print\(f"Sync', 'logger.debug(f"Sync'),
        (r'print\(f"Syncing', 'logger.debug(f"Syncing'),
        (r'print\(f"Synced', 'logger.debug(f"Synced'),
        (r'print\(f"Looking', 'logger.debug(f"Looking'),
        (r'print\(f"Searching', 'logger.debug(f"Searching'),
        (r'print\(f"Querying', 'logger.debug(f"Querying'),
        
        # Catch-all for any remaining [TAG] patterns
        # Use a general regex that matches print(f"[anything]
        # This should catch most remaining bracketed tags
    ]
    
    # After specific replacements, do a catch-all for remaining [TAG] patterns
    # Match print(f"[any_tag] and convert to logger.debug
    content = re.sub(
        r'print\(f"\[([A-Z_a-z0-9 ]+)\]',
        r'logger.debug(f"[\1]',
        content
    )
    
    for pattern, replacement in replacements:
        content = re.sub(pattern, replacement, content)
    
    # Count remaining print statements
    remaining_count = len(re.findall(r'print\(f?"', content))
    converted = original_count - remaining_count
    print(f"Converted {converted} print statements")
    print(f"Remaining: {remaining_count}")
    
    # Write the file back
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"[OK] {filepath} updated successfully")
    return converted, remaining_count

def main():
    """Main function to convert all route files."""
    routes_dir = 'routes'
    
    # Files to process
    route_files = [
        'handover.py',
        'dashboard.py', 
        'reports.py',
        'keypoints.py',
        'auth.py',
        'roster_upload.py',
        'team_roster.py',
        'team_simple.py',
        'user_management.py',
        'admin.py',
        'admin_secrets.py',
        'checkin.py',
        'user_profile.py',
        'incident_assignment.py',
        'misc.py',
        'roster.py',
        'escalation_matrix.py',
        'vendor_details.py',
        'assignment_response.py',
        'shift_swap_leave.py',
        'email_config_routes.py',
        'shift_config.py',
        'sso_auth.py',
        'sso_config.py',
        'admin_linking.py',
        'onboarding.py',
        'config.py',
    ]
    
    total_converted = 0
    total_remaining = 0
    
    for filename in route_files:
        filepath = os.path.join(routes_dir, filename)
        if os.path.exists(filepath):
            result = convert_file(filepath)
            if result:
                total_converted += result[0]
                total_remaining += result[1]
        else:
            print(f"[WARN] File not found: {filepath}")
    
    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"Total converted: {total_converted}")
    print(f"Total remaining: {total_remaining}")

if __name__ == '__main__':
    main()

