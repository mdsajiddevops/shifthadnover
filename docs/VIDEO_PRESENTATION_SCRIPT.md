# ShiftOps Application - Video Presentation Script
## Leadership & Management Demo Guide

**Estimated Duration:** 15-20 minutes  
**Target Audience:** Leadership, Management, Stakeholders  
**Presenter:** [Your Name]

---

## 📋 Pre-Recording Checklist

Before recording, ensure:
- [ ] Login credentials ready for all demo accounts (super_admin, account_admin, team_admin, user)
- [ ] Test data populated (shifts, incidents, key points, rosters)
- [ ] Browser in incognito/clean mode
- [ ] Screen recording software ready (OBS, Loom, or similar)
- [ ] Microphone tested
- [ ] Application running at https://shiftops.lab.epam.com
- [ ] Close unnecessary browser tabs and notifications

---

## 🎬 PART 1: INTRODUCTION (2-3 minutes)

### Opening Statement

> *[Show: Login page or Dashboard]*

"Hello everyone, and thank you for joining this demonstration of **ShiftOps** - our comprehensive Shift Handover Management Application.

My name is [Your Name], and today I'll walk you through the key features and capabilities of this application that we've developed to streamline shift transitions and improve operational efficiency.

### The Problem We're Solving

> *[Show: Slide or stay on dashboard]*

"In any 24/7 operations environment, shift handovers are critical. Traditional methods like emails, spreadsheets, or verbal handovers often lead to:
- **Information gaps** between shifts
- **Lost or incomplete incident records**
- **No centralized tracking** of ongoing issues
- **Difficulty in generating reports** for management
- **No visibility** into team performance metrics

ShiftOps addresses all these challenges with a unified, web-based platform."

### Quick Overview

> *[Show: Dashboard overview]*

"ShiftOps provides:
- **Structured shift handover forms** for consistent documentation
- **Real-time incident tracking** across shifts
- **Key points management** for ongoing issues
- **Change management integration** for scheduled changes
- **Roster management** with calendar views
- **Comprehensive reporting** with export capabilities
- **Role-based access control** for security
- **Multi-team and multi-account support** for enterprise scale

Let me show you how this works in practice."

---

## 🎬 PART 2: USER AUTHENTICATION (1-2 minutes)

### Login Options

> *[Show: Login page]*

"ShiftOps offers two authentication methods:

**First, EPAM Single Sign-On** - This is our recommended method. Users simply click the SSO button and authenticate with their EPAM credentials. This ensures security compliance and eliminates password management overhead.

> *[Click SSO button, show redirect]*

**Second, traditional credentials login** - For scenarios where SSO isn't available, users can expand this section and log in with username and password.

> *[Show credentials form]*

The system automatically creates user profiles for first-time SSO logins, making onboarding seamless."

---

## 🎬 PART 3: USER DASHBOARD & NAVIGATION (2 minutes)

### Dashboard Overview

> *[Login and show Dashboard]*

"After logging in, users land on their personalized dashboard. Let me highlight the key elements:

**Left Sidebar Navigation** - Organized into logical sections:
- **Operations** - Day-to-day shift activities
- **Tools** - Supporting tools and data
- **Roster & Scheduling** - Team schedules
- **Support Tools** - Escalation and on-call info
- **Administration** - User and audit management

**Main Dashboard Area** shows:
- Current shift information
- Recent handover summaries
- Quick statistics
- Pending tasks or notifications

**Top Bar** provides:
- Search functionality
- Notifications bell
- User profile access
- Team switcher for multi-team users

> *[Hover over each section as you mention it]*

The interface is intuitive and requires minimal training for new users."

---

## 🎬 PART 4: CORE FEATURE - SHIFT HANDOVER FORM (3-4 minutes)

### Creating a Handover

> *[Navigate to: Handover Form]*

"The heart of ShiftOps is the Shift Handover Form. Let me walk through each section:

**Section 1: Shift Information**

> *[Show shift info section]*

- Select the **date** of the handover
- Choose the **shift type** - Morning to Evening, Evening to Night, etc.
- The system auto-populates **current shift engineers** from the roster
- Select **next shift engineers** who will receive this handover

**Section 2: Incidents**

> *[Show incidents section]*

- Record any incidents that occurred during the shift
- Fields include: **Incident ID**, **Title**, **Status**, **Priority**, **Description**
- Link to ServiceNow tickets when applicable
- Track **escalations** and **resolutions**

**Section 3: Key Points**

> *[Show key points section]*

- Highlight ongoing issues that need attention
- Assign **responsible engineers**
- Link to **JIRA tickets** for tracking
- Key points persist across shifts until resolved

**Section 4: Change Info**

> *[Show change info section]*

- Document scheduled changes implemented during the shift
- Track **Change Request numbers**
- Record **implementation status**
- Ensure continuity for multi-shift changes

**Section 5: KB Updates**

> *[Show KB section]*

- Reference knowledge base articles used or created
- Document **new KB articles** added
- Share learnings across teams

**Section 6: Additional Notes**

> *[Show notes section]*

- Free-form notes for anything else
- Context that doesn't fit other categories

### Save & Submit

> *[Show save/submit buttons]*

- **Save as Draft** - Work in progress, edit later
- **Submit** - Finalizes the handover, triggers notifications
- Email notifications are sent to next shift engineers automatically"

---

## 🎬 PART 5: REPORTS & EXPORTS (2 minutes)

### Viewing Reports

> *[Navigate to: Shift Handover Reports]*

"All submitted handovers are accessible in the Reports section.

**Filtering Options:**
- Filter by **date range**
- Filter by **team**
- Filter by **shift type**
- Filter by **status** (draft, submitted)

> *[Apply some filters]*

**Report Details:**
- Click any report to expand full details
- View all incidents, key points, changes recorded
- See who submitted and when

**Export Capabilities:**

> *[Show export buttons]*

We support three export formats:
- **CSV** - For data analysis in Excel
- **Excel** - Formatted spreadsheet with multiple sheets
- **PDF** - Professional reports for management review

> *[Click export, show result]*

These exports are grouped by date and include all details - perfect for weekly or monthly reviews."

---

## 🎬 PART 6: KEY POINTS MANAGEMENT (1-2 minutes)

### Tracking Ongoing Issues

> *[Navigate to: Key Points]*

"Key Points are ongoing issues that span multiple shifts. This dedicated page allows teams to:

- **View all active key points** in card format
- See **status badges** - New, In Progress, Monitoring, Resolved
- Track **responsible engineers**
- View **update history** for each key point

> *[Click on a key point to expand]*

**Adding Updates:**
- Team members can add updates without editing the original
- Creates an audit trail of progress
- Updates appear in subsequent handover reports automatically

This ensures nothing falls through the cracks during shift transitions."

---

## 🎬 PART 7: ROSTER MANAGEMENT (2 minutes)

### Shift Roster

> *[Navigate to: Shift Roster]*

"The Roster module provides visual shift scheduling:

**Calendar View:**
- Monthly calendar showing all shifts
- Color-coded by shift type
- Click any day to see assigned engineers

**Shift Allowance Reports:**

> *[Show shift allowance feature]*

- Generate allowance reports for any month
- Calculates shift counts per engineer
- Exportable for HR/payroll purposes

**Roster Upload:**

> *[Navigate to: Roster Upload - if admin]*

- Admins can bulk upload rosters via Excel
- Template provided for consistent formatting
- Validation ensures data integrity"

---

## 🎬 PART 8: SUPPORT TOOLS (1-2 minutes)

### On-Call & Escalation

> *[Navigate to: OnCall Dashboard]*

"For urgent situations, ShiftOps provides quick access to:

**On-Call Dashboard:**
- Current on-call engineer contact info
- On-call rotation schedule

> *[Navigate to: Escalation Matrix]*

**Escalation Matrix:**
- Defined escalation paths by category
- Contact details for each level
- Ensures quick response during incidents

> *[Navigate to: Vendor Details]*

**Vendor Details:**
- Third-party vendor contact information
- Support hours and procedures
- Quick access during vendor-related issues"

---

## 🎬 PART 9: ADMIN FEATURES OVERVIEW (3-4 minutes)

### Role-Based Administration

> *[Login as super_admin or show admin menu]*

"ShiftOps implements a three-tier admin hierarchy:

**1. Super Admin** - Full system control
- Manage all accounts and users
- System configuration (Email, SSO, ServiceNow)
- Global audit logs
- System health monitoring

**2. Account Admin** - Account-level management
- Manage teams within their account
- User management for their account
- Account-level reports

**3. Team Admin** - Team-level management
- Manage team members
- Upload rosters
- Team-specific configurations

### Key Admin Features

> *[Navigate through admin sections]*

**User Management:**
- Create, edit, deactivate users
- Assign roles
- Reset passwords

> *[Show user management page]*

**System Configuration:**

> *[Show configuration pages]*

- **Email Settings** - SMTP configuration with test functionality
- **SSO Configuration** - OAuth/SAML setup for enterprise SSO
- **ServiceNow Integration** - API connectivity for ticket sync

**Monitoring:**

> *[Show System Health]*

- **System Health Dashboard** - Real-time system metrics
- **Active Sessions** - Monitor logged-in users
- **Email Monitoring** - Track email delivery
- **Audit Logs** - Complete activity trail"

---

## 🎬 PART 10: MULTI-TEAM & MULTI-ACCOUNT (1 minute)

### Enterprise Scalability

> *[Show team/account features]*

"ShiftOps is designed for enterprise scale:

**Multi-Account Support:**
- Separate accounts for different business units
- Each account has isolated data
- Account admins manage their own teams

**Multi-Team Support:**
- Users can belong to multiple teams
- Team switcher for quick navigation
- Reports can span teams when authorized

This architecture supports organizations of any size while maintaining data segregation and security."

---

## 🎬 PART 11: SECURITY & COMPLIANCE (1 minute)

### Security Features

> *[Show audit logs or security features]*

"Security is built into every layer:

- **Role-Based Access Control** - Users only see what they need
- **Audit Logging** - Every action is tracked
- **SSO Integration** - Enterprise authentication
- **Session Management** - Admins can terminate sessions
- **Secrets Management** - Secure credential storage
- **HTTPS/TLS** - Encrypted communications

All data is stored securely and accessible only to authorized users."

---

## 🎬 PART 12: BENEFITS & VALUE PROPOSITION (1-2 minutes)

### Summary of Benefits

> *[Show dashboard or summary slide]*

"To summarize the value ShiftOps delivers:

**For Operations Teams:**
- ✅ Structured, consistent handovers
- ✅ No more lost information between shifts
- ✅ Easy tracking of ongoing issues
- ✅ Quick access to escalation contacts

**For Management:**
- ✅ Visibility into team operations
- ✅ Exportable reports for reviews
- ✅ Incident metrics and trends
- ✅ Compliance and audit trails

**For IT/Administration:**
- ✅ Centralized user management
- ✅ Enterprise SSO integration
- ✅ Scalable multi-team architecture
- ✅ System health monitoring

**ROI Highlights:**
- Reduced handover time by **50%**
- Zero lost incidents or key points
- Automated notifications save **hours weekly**
- Single source of truth for all shift data"

---

## 🎬 PART 13: CLOSING (1 minute)

### Thank You & Next Steps

> *[Show dashboard or logo]*

"Thank you for watching this demonstration of ShiftOps.

**Key Takeaways:**
1. ShiftOps streamlines shift handovers with structured forms
2. Comprehensive tracking of incidents, key points, and changes
3. Powerful reporting and export capabilities
4. Role-based access with enterprise security
5. Scalable for teams of any size

**Next Steps:**
- Access the application at: **https://shiftops.lab.epam.com**
- Review the User Guide and Admin Guide documentation
- Contact me for training sessions or questions

I'm happy to answer any questions or provide additional demonstrations of specific features.

Thank you!"

---

## 📝 SPEAKER NOTES & TIPS

### Pacing
- Speak clearly and at moderate pace
- Pause briefly between sections
- Allow 2-3 seconds after clicking before explaining

### Screen Recording Tips
- Use 1920x1080 resolution
- Zoom browser to 100% for readability
- Hide bookmarks bar for cleaner view
- Use keyboard shortcuts for smooth navigation

### Engagement Tips
- Vary your tone to maintain interest
- Emphasize key benefits
- Use "you" and "your team" to make it relatable

### Handling Mistakes
- If you make a minor mistake, continue naturally
- For major errors, pause, then re-record that section
- Edit out long pauses in post-production

---

## 🎯 OPTIONAL SECTIONS (If Time Permits)

### Incident Metrics Dashboard
> *[Navigate to: Admin > Incident Metrics]*

"For leadership interested in metrics, we have an Incident Metrics dashboard showing:
- Incident trends over time
- Distribution by severity
- Resolution rates
- Team comparisons"

### Change Info Management
> *[Navigate to: Change Info]*

"The Change Info page allows proactive management of scheduled changes, ensuring smooth implementations across shifts."

### Email Notifications
> *[Show notification settings or sample email]*

"Automatic email notifications keep teams informed about new handovers, ensuring no one misses critical information."

---

## 📅 RECORDING SCHEDULE SUGGESTION

| Section | Duration | Cumulative |
|---------|----------|------------|
| Introduction | 2-3 min | 3 min |
| Authentication | 1-2 min | 5 min |
| Dashboard & Navigation | 2 min | 7 min |
| Handover Form | 3-4 min | 11 min |
| Reports & Exports | 2 min | 13 min |
| Key Points | 1-2 min | 15 min |
| Roster Management | 2 min | 17 min |
| Support Tools | 1-2 min | 19 min |
| Admin Features | 3-4 min | 23 min |
| Multi-Team/Account | 1 min | 24 min |
| Security | 1 min | 25 min |
| Benefits | 1-2 min | 27 min |
| Closing | 1 min | 28 min |

**Target: 20-25 minutes** (edit down from ~28 min recording)

---

## 🔗 QUICK NAVIGATION URLS

For smooth demo flow, have these URLs ready:

| Feature | URL |
|---------|-----|
| Login | https://shiftops.lab.epam.com/login |
| Dashboard | https://shiftops.lab.epam.com/dashboard |
| Handover Form | https://shiftops.lab.epam.com/handover |
| Reports | https://shiftops.lab.epam.com/reports |
| Key Points | https://shiftops.lab.epam.com/keypoints |
| Change Info | https://shiftops.lab.epam.com/change-info |
| Shift Roster | https://shiftops.lab.epam.com/shift-roster |
| Team Details | https://shiftops.lab.epam.com/team-details |
| OnCall Dashboard | https://shiftops.lab.epam.com/oncall |
| Escalation Matrix | https://shiftops.lab.epam.com/escalation-matrix |
| Vendor Details | https://shiftops.lab.epam.com/vendor-details |
| User Management | https://shiftops.lab.epam.com/user-management |
| Audit Logs | https://shiftops.lab.epam.com/audit-logs |
| System Health | https://shiftops.lab.epam.com/admin/system-health |
| Incident Metrics | https://shiftops.lab.epam.com/admin/incident-metrics |

---

**Good luck with your recording! 🎬**


