# Feature Management Guide

## Overview

The Feature Management system allows superadmins to control which tabs and features are visible for specific accounts and teams. This provides fine-grained control over the application's UI based on organizational needs.

## Features

- **Account-level configuration**: Set default features for all teams under an account
- **Team-level configuration**: Override account defaults for specific teams
- **Hierarchy**: Team-level settings override account-level settings
- **Bulk operations**: Enable/disable all features at once
- **Reset to defaults**: Remove custom configurations

## Access

1. Login as **super_admin**
2. Navigate to **Administration** → **Feature Management**

## How It Works

### Feature Hierarchy

When checking if a feature is enabled, the system checks in this order:
1. **Team-level configuration** (highest priority)
2. **Account-level configuration**
3. **Global default** (defaults to enabled)

### Available Features/Tabs

The following features can be controlled:

#### Operations
- Handover Form
- Shift Reports
- Change Info
- KB Updates
- Key Points
- Problem Tickets

#### Team Management
- Shift Roster
- Roster Upload
- Team Details
- On-Call Dashboard

#### Tools
- ServiceNow Integration
- Escalation Matrix
- Vendor Details
- CTask Assignment
- Audit Logs
- Shift Management

#### Knowledge Base
- KB Articles
- Applications

#### Advanced
- Change Management
- Post-mortems

## Usage

### Step 1: Select Scope

1. Choose **Scope Type**: Account Level or Team Level
2. Select the specific **Account** or **Team** from the dropdown

### Step 2: Configure Features

- Each feature will appear with a toggle switch
- **Green (ON)**: Feature is enabled for this scope
- **Gray (OFF)**: Feature is disabled for this scope

### Step 3: Save Changes

- Changes are saved automatically when you toggle a feature
- You'll see a success message confirming the update

### Bulk Operations

- **Enable All**: Enable all features for the selected scope
- **Disable All**: Disable all features for the selected scope
- **Reset to Defaults**: Remove all custom configurations (reverts to global defaults)

## Examples

### Example 1: Disable Problem Tickets for a Specific Team

1. Select **Scope Type**: Team Level
2. Select the team (e.g., "Team Alpha")
3. Find "Problem Tickets" in the Operations section
4. Toggle it OFF
5. Users in Team Alpha will no longer see the Problem Tickets tab

### Example 2: Enable All Features for an Account

1. Select **Scope Type**: Account Level
2. Select the account (e.g., "Account A")
3. Click **Enable All**
4. All teams under Account A will have all features enabled

### Example 3: Team Override

1. Set Account-level: Disable "Vendor Details"
2. Set Team-level for "Team Beta": Enable "Vendor Details"
3. Result: Only Team Beta sees Vendor Details, other teams in the account don't

## Database Schema

The configuration is stored in the `team_feature_config` table:

```sql
CREATE TABLE team_feature_config (
    id INT PRIMARY KEY AUTO_INCREMENT,
    scope_type VARCHAR(20) NOT NULL,  -- 'account' or 'team'
    scope_id INT NOT NULL,            -- account_id or team_id
    feature_key VARCHAR(128) NOT NULL, -- e.g., 'tab_problem_tickets'
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_by VARCHAR(255),
    updated_by VARCHAR(255),
    UNIQUE KEY (scope_type, scope_id, feature_key)
);
```

## Route Protection

Routes can be protected using the `@feature_required` decorator:

```python
from app import feature_required

@handover_bp.route('/problem-tickets')
@login_required
@feature_required('tab_problem_tickets')
def problem_tickets():
    # This route will only be accessible if tab_problem_tickets is enabled
    # for the user's team/account
    return render_template('problem_tickets.html')
```

## Migration

To set up the database table, run:

```sql
source migrations/create_team_feature_config_table.sql
```

Or use the Python migration script:

```python
from models.models import db
from models.team_feature_config import TeamFeatureConfig

# Create tables
db.create_all()
```

## Troubleshooting

### Feature Not Showing/Hiding

1. Check if the feature is enabled for the user's team
2. Check if the feature is enabled for the user's account
3. Check the browser console for JavaScript errors
4. Verify the database table exists and has the correct schema

### Changes Not Taking Effect

1. Clear browser cache
2. Verify the user's team/account assignment
3. Check database for the configuration entry
4. Restart the application if needed

## Best Practices

1. **Start with Account-level**: Set defaults at the account level first
2. **Use Team-level sparingly**: Only override when necessary
3. **Document changes**: Use the description field to note why a feature was disabled
4. **Test thoroughly**: Verify changes work for different user roles
5. **Monitor usage**: Check audit logs to see who made changes

## API Endpoints

### Get Feature Configuration
```
GET /api/feature-management/config?scope_type=account&scope_id=1
```

### Set Feature Configuration
```
POST /api/feature-management/config
{
    "scope_type": "team",
    "scope_id": 5,
    "feature_key": "tab_problem_tickets",
    "is_enabled": false
}
```

### Bulk Update
```
POST /api/feature-management/config/bulk
{
    "scope_type": "account",
    "scope_id": 1,
    "feature_updates": {
        "tab_problem_tickets": true,
        "tab_vendor_details": false
    }
}
```

## Support

For issues or questions, contact the system administrator or refer to the main documentation.
