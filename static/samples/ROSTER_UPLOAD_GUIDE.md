# Shift Roster Upload Guide

## Overview
The Shift Roster Upload feature allows administrators to upload shift schedules in bulk using Excel files (.xlsx format). This guide explains the supported formats and provides examples.

## Sample File
A sample Excel file is available for download from the Roster Upload page. This file contains:
- **Long Format Sheet**: Recommended format with examples
- **Wide Format Sheet**: Alternative format with examples  
- **Instructions Sheet**: Detailed documentation and guidelines

## Supported File Formats

### 1. Long Format (Recommended)
This format uses one row per person per day assignment.

**Required Columns:**
- `Date`: Date in YYYY-MM-DD format (e.g., 2025-11-01)
- `Team Member`: Full name of the team member (must exist in system)
- `Shift`: Shift code (see codes below)

**Example:**
```
Date        | Team Member   | Shift
2025-11-01  | John Smith    | D
2025-11-01  | Jane Doe      | E
2025-11-02  | John Smith    | N
```

### 2. Wide Format (Alternative)
This format uses dates as column headers with team members as rows.

**Required Columns:**
- `Member Name`: Full name of the team member (first column)
- Date columns: Each date as a separate column header (YYYY-MM-DD)

**Example:**
```
Member Name | 2025-11-01 | 2025-11-02 | 2025-11-03
John Smith  | D          | E          | N
Jane Doe    | E          | N          | G
```

## Shift Codes

| Code | Description |
|------|-------------|
| D    | Day Shift |
| E    | Evening Shift |
| N    | Night Shift |
| G    | General/Flexible Shift |
| LE   | Leave |
| VL   | Vacation Leave |
| HL   | Holiday Leave |
| CO   | Comp Off |
| (blank) | Off Day |

## Upload Process

1. **Access**: Navigate to the Roster Upload page (requires admin privileges)
2. **Select Account/Team**: Choose the appropriate account and team (if applicable)
3. **Download Sample**: Download the sample file for reference (optional but recommended)
4. **Prepare File**: Create your roster file following one of the supported formats
5. **Upload**: Select your .xlsx file and click "Upload Shift Roster"
6. **Preview**: Review the parsed data in the preview table
7. **Confirm**: The system will validate and import the roster data

## Important Notes

- **File Format**: Only .xlsx files are supported
- **Team Members**: All team member names must exist in the system
- **Date Format**: Dates must be in proper Excel date format
- **Validation**: The system validates all data before importing
- **Permissions**: Only super_admin, account_admin, and team_admin roles can upload rosters
- **Overwrite**: Uploading a roster for existing dates will overwrite previous assignments

## Troubleshooting

### Common Issues:
1. **Missing Columns**: Ensure all required columns are present
2. **Invalid Dates**: Check date format and ensure dates are recognizable
3. **Unknown Team Members**: Verify team member names match exactly
4. **Invalid Shift Codes**: Use only the supported shift codes listed above
5. **Permission Denied**: Ensure you have admin privileges

### Error Messages:
- "Missing required columns": Add the missing columns to your file
- "Team member not found": Check team member names against the system
- "Invalid date format": Ensure dates are in proper format
- "Account/Team selection required": Select account and team before uploading

## Best Practices

1. **Use the Sample File**: Download and modify the sample file as a starting point
2. **Test with Small Data**: Test with a few entries before uploading large rosters
3. **Backup Existing Data**: Consider exporting current roster before overwriting
4. **Validate Names**: Ensure all team member names exist in the system
5. **Check Dates**: Verify date ranges are correct before uploading
6. **Review Preview**: Always review the preview table before confirming upload

## Data Validation

The system performs the following validations:
- File format (.xlsx only)
- Required columns presence
- Date format validation
- Team member existence check
- Shift code validation
- Account and team assignment verification

## Support

If you encounter issues:
1. Check this documentation first
2. Download and examine the sample file
3. Verify your data against the requirements
4. Contact system administrator for assistance