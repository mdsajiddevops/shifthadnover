# Shift Handover Application - Database Tables Reference

This document provides a comprehensive list of all database tables in the Shift Handover application, organized by category.

---

## 🏢 Core Organization Tables

| Table Name | Model | Description |
|------------|-------|-------------|
| `account` | `Account` | Organization/company accounts |
| `team` | `Team` | Teams within accounts |
| `user` | `User` | User accounts |
| `user_team_memberships` | `UserTeamMembership` | Multi-team user assignments |
| `team_member` | `TeamMember` | Team member roster records |

---

## 📋 Shift Handover Core Tables

| Table Name | Model | Description |
|------------|-------|-------------|
| `shift` | `Shift` | Main handover submission record |
| `incident` | `Incident` | Incidents (Active, Closed, Priority, Handover) |
| `shift_key_point` | `ShiftKeyPoint` | Key points/action items |
| `shift_key_point_update` | `ShiftKeyPointUpdate` | Updates on key points |
| `shift_change_info` | `ShiftChangeInfo` | Change-related information |
| `shift_kb_update` | `ShiftKBUpdate` | Knowledge Base updates |
| `current_shift_engineers` | Association Table | Current shift engineer assignments |
| `next_shift_engineers` | Association Table | Next shift engineer assignments |

### Shift Table Details
```
shift
├── id (Primary Key)
├── date
├── current_shift_type (Morning/Evening/Night)
├── next_shift_type
├── status (draft/sent)
├── submitted_at
├── created_at
├── account_id (FK → account)
├── team_id (FK → team)
└── additional_notes
```

### Incident Table Details
```
incident
├── id (Primary Key)
├── title
├── status (Active/Closed)
├── priority
├── handover (text)
├── shift_id (FK → shift)
├── type (Active, Closed, Priority, Handover)
├── account_id (FK → account)
├── team_id (FK → team)
├── description
├── assigned_to
└── escalated_to
```

---

## 🔄 Enhanced Handover Workflow Tables

| Table Name | Model | Description |
|------------|-------|-------------|
| `handover_request` | `HandoverRequest` | Enhanced handover with incident assignments |
| `incident_assignment` | `IncidentAssignment` | Incident assignment to engineers |
| `incident_assignment_response` | `IncidentAssignmentResponse` | Engineer responses to assignments |
| `handover_incident_response_log` | `HandoverIncidentResponseLog` | Complete audit of incident handovers |
| `handover_response` | `HandoverResponse` | Overall handover responses |
| `handover_notification` | `HandoverNotification` | Handover-related notifications |
| `handover_audit_log` | `HandoverAuditLog` | Audit log for handover actions |

### Handover Request Table Details
```
handover_request
├── id (Primary Key)
├── shift_date
├── current_shift_type
├── next_shift_type
├── created_by_id (FK → user)
├── status (pending/partially_accepted/fully_accepted/rejected/expired)
├── general_notes
├── shift_summary
├── created_at
├── updated_at
├── expires_at
├── account_id (FK → account)
└── team_id (FK → team)
```

### Incident Assignment Table Details
```
incident_assignment
├── id (Primary Key)
├── handover_request_id (FK → handover_request)
├── incident_id (ServiceNow ID)
├── incident_title
├── incident_description
├── incident_priority
├── incident_status
├── incident_url
├── assigned_to_id (FK → user)
├── assigned_by_id (FK → user)
├── assignment_notes
├── handover_context
├── assignment_status (pending/accepted/rejected/reassigned)
├── assigned_at
├── responded_at
├── account_id (FK → account)
└── team_id (FK → team)
```

### Handover Incident Response Log Table Details
```
handover_incident_response_log
├── id (Primary Key)
├── response_date
├── response_datetime
├── from_shift_type
├── to_shift_type
├── from_shift_id (FK → shift)
├── to_shift_id (FK → shift)
├── assigned_by_id (FK → user)
├── assigned_by_name
├── accepted_by_id (FK → user)
├── accepted_by_name
├── incident_number
├── incident_title
├── incident_description
├── incident_priority
├── incident_type
├── incident_category
├── assignment_status
├── response_status
├── response_comments
├── assignment_notes
├── assigned_at
├── responded_at
├── estimated_completion
├── actual_completion
├── handover_request_id (FK → handover_request)
├── incident_assignment_id (FK → incident_assignment)
├── incident_assignment_response_id (FK → incident_assignment_response)
├── account_id (FK → account)
├── team_id (FK → team)
├── created_at
└── updated_at
```

---

## 📅 Shift Roster & Scheduling Tables

| Table Name | Model | Description |
|------------|-------|-------------|
| `shift_roster` | `ShiftRoster` | Monthly shift assignments (D, E, N, etc.) |
| `team_shift_configs` | `TeamShiftConfig` | Team shift configuration |
| `team_shift_timing_configs` | `TeamShiftTimingConfig` | Shift timing configurations |
| `roster_assignments` | `RosterAssignment` | Roster assignments |
| `checkin_log` | `CheckInLog` | Check-in/check-out history |

### Shift Roster Table Details
```
shift_roster
├── id (Primary Key)
├── team_member_id (FK → team_member)
├── date
├── shift_code (D/E/N/LE/G/O/VL, etc.)
├── month
├── year
├── account_id (FK → account)
├── team_id (FK → team)
└── created_at
```

---

## 🔄 Shift Swap & Leave Tables

| Table Name | Model | Description |
|------------|-------|-------------|
| `shift_swap_request` | `ShiftSwapRequest` | Shift swap requests |
| `leave_request` | `LeaveRequest` | Leave/time-off requests |
| `swap_leave_notification` | `SwapLeaveNotification` | Swap/leave notifications |
| `swap_leave_audit_log` | `SwapLeaveAuditLog` | Audit log for swap/leave |

### Shift Swap Request Table Details
```
shift_swap_request
├── id (Primary Key)
├── requester_id (FK → user)
├── swap_with_id (FK → user)
├── original_date
├── original_shift_code
├── swap_date
├── swap_shift_code
├── status (pending/approved/rejected/cancelled)
├── reason
├── approved_by_id (FK → user)
├── approved_at
├── created_at
├── updated_at
├── account_id (FK → account)
└── team_id (FK → team)
```

### Leave Request Table Details
```
leave_request
├── id (Primary Key)
├── requester_id (FK → user)
├── leave_type (sick/vacation/personal/other)
├── start_date
├── end_date
├── reason
├── status (pending/approved/rejected/cancelled)
├── approved_by_id (FK → user)
├── approved_at
├── created_at
├── updated_at
├── account_id (FK → account)
└── team_id (FK → team)
```

---

## 🔧 ServiceNow Integration Tables

| Table Name | Model | Description |
|------------|-------|-------------|
| `servicenow_config` | `ServiceNowConfig` | ServiceNow connection settings |
| `servicenow_incidents` | `ServiceNowIncident` | Synced ServiceNow incidents |
| `servicenow_sync_logs` | `ServiceNowSyncLog` | Sync history logs |
| `servicenow_assignment_groups` | `ServiceNowAssignmentGroup` | Assignment groups |

---

## ⚙️ Configuration & Settings Tables

| Table Name | Model | Description |
|------------|-------|-------------|
| `app_config` | `AppConfig` | Application configuration |
| `sso_config` | `SSOConfig` | SSO/authentication settings |
| `smtp_config` | `SMTPConfig` | SMTP email settings |
| `team_email_config` | `TeamEmailConfig` | Team-specific email settings |
| `escalation_matrix_file` | `EscalationMatrixFile` | Escalation matrix files |

---

## 📊 Reference Data Tables

| Table Name | Model | Description |
|------------|-------|-------------|
| `application_detail` | `ApplicationDetail` | Application/system details |
| `kb_detail` | `KBDetail` | Knowledge base articles |
| `vendor_detail` | `VendorDetail` | Vendor information |

---

## 🔐 Security & Audit Tables

| Table Name | Model | Description |
|------------|-------|-------------|
| `secret_store` | `SecretStore` | Encrypted secrets storage |
| `secret_audit_log` | `SecretAuditLog` | Secret access audit log |
| `audit_log` | `AuditLog` | General audit log |
| `email_config_audit_log` | `EmailConfigAuditLog` | Email config changes audit |
| `password_reset_tokens` | `PasswordResetToken` | Password reset tokens |

---

## 📊 Total Tables Count: ~40+

---

## Data Flow Diagrams

### Handover Form Submission Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    HANDOVER FORM SUBMISSION                      │
└─────────────────────────────────────────────────────────────────┘
                              │
     ┌────────────────────────┼────────────────────────┐
     ▼                        ▼                        ▼
┌─────────┐           ┌──────────────┐         ┌─────────────┐
│  shift  │           │handover_     │         │ audit_log   │
│ (main)  │           │request       │         │             │
└────┬────┘           │(enhanced)    │         └─────────────┘
     │                └──────┬───────┘
     │                       │
┌────┴────────────────┬──────┴────────────────┬───────────────┐
▼                     ▼                       ▼               ▼
┌──────────┐   ┌─────────────┐   ┌──────────────────┐  ┌────────────┐
│incident  │   │shift_key_   │   │incident_         │  │shift_      │
│          │   │point        │   │assignment        │  │change_info │
└──────────┘   └─────────────┘   └──────────────────┘  └────────────┘
                    │                    │                    │
                    ▼                    ▼                    ▼
            ┌─────────────┐    ┌──────────────────────┐ ┌────────────┐
            │shift_key_   │    │incident_assignment_  │ │shift_kb_   │
            │point_update │    │response              │ │update      │
            └─────────────┘    └──────────────────────┘ └────────────┘
                                        │
                                        ▼
                               ┌──────────────────────┐
                               │handover_incident_    │
                               │response_log          │
                               └──────────────────────┘
```

### User to Teams Relationship

```
┌──────────┐       ┌─────────────────────┐       ┌──────────┐
│   User   │──────▶│ user_team_          │◀──────│   Team   │
│          │       │ memberships         │       │          │
└──────────┘       │ (is_primary flag)   │       └──────────┘
                   └─────────────────────┘
                              │
                              ▼
                   ┌─────────────────────┐
                   │    team_member      │
                   │ (roster entries)    │
                   └─────────────────────┘
                              │
                              ▼
                   ┌─────────────────────┐
                   │    shift_roster     │
                   │ (daily shifts)      │
                   └─────────────────────┘
```

### Shift Swap Request Flow

```
┌──────────────┐     ┌────────────────────┐     ┌──────────────┐
│  Requester   │────▶│ shift_swap_request │◀────│  Swap With   │
│   (User)     │     │                    │     │   (User)     │
└──────────────┘     └─────────┬──────────┘     └──────────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ swap_leave_          │
                    │ notification         │
                    └──────────────────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ swap_leave_          │
                    │ audit_log            │
                    └──────────────────────┘
```

---

## Model File Locations

| File | Models Contained |
|------|------------------|
| `models/models.py` | Account, Team, User, TeamMember, Shift, Incident, ShiftKeyPoint, ShiftChangeInfo, ShiftKBUpdate, etc. |
| `models/handover_enhanced.py` | HandoverRequest, IncidentAssignment, HandoverResponse, HandoverNotification, HandoverAuditLog, etc. |
| `models/shift_swap_leave.py` | ShiftSwapRequest, LeaveRequest, SwapLeaveNotification, SwapLeaveAuditLog |
| `models/servicenow_models.py` | ServiceNowIncident, ServiceNowSyncLog, ServiceNowAssignmentGroup |
| `models/sso_config.py` | SSOConfig |
| `models/smtp_config.py` | SMTPConfig |
| `models/email_config.py` | TeamEmailConfig, EmailConfigAuditLog |
| `models/team_roster_models.py` | TeamShiftConfig, RosterAssignment |
| `models/team_shift_timing_config.py` | TeamShiftTimingConfig |
| `models/audit_log.py` | AuditLog |
| `models/app_config.py` | AppConfig |
| `models/application_detail.py` | ApplicationDetail |
| `models/kb_detail.py` | KBDetail |
| `models/vendor_detail.py` | VendorDetail |
| `models/password_reset.py` | PasswordResetToken |
| `models/secrets_manager.py` | SecretStore, SecretAuditLog |

---

*Last Updated: December 2025*







