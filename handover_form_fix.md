# Handover Form Fix for Automatic Notifications

## Problem
The handover form creates incidents but doesn't automatically assign them to next shift engineers, 
so no incident assignments or notifications are created.

## Solution
Modify the handover form to automatically assign open incidents to next shift engineers when 
the "assigned to" field is left empty.

## Code Changes Needed

### In routes/handover.py around line 490:

**Current code:**
```python
assigned_engineer = assigned_tos[i] if i < len(assigned_tos) and assigned_tos[i].strip() else None
if assigned_engineer:
    # Create enhanced incident assignment only if engineer is assigned
```

**Updated code:**
```python
assigned_engineer = assigned_tos[i] if i < len(assigned_tos) and assigned_tos[i].strip() else None

# If no specific engineer assigned, auto-assign to first next shift engineer
if not assigned_engineer and next_engineers_objs:
    assigned_engineer = next_engineers_objs[0].name
    print(f"[DEBUG] Auto-assigning incident to next shift engineer: {assigned_engineer}")

if assigned_engineer:
    # Create enhanced incident assignment
```

### Alternative: Auto-assign to all next shift engineers

If you want to notify ALL next shift engineers:
```python
# Auto-assign to all next shift engineers if no specific assignment
engineers_to_assign = []
if assigned_engineer:
    engineers_to_assign = [assigned_engineer]
elif next_engineers_objs:
    engineers_to_assign = [eng.name for eng in next_engineers_objs]
    print(f"[DEBUG] Auto-assigning incident to all next shift engineers: {engineers_to_assign}")

for engineer in engineers_to_assign:
    # Create enhanced incident assignment for each engineer
```

## Testing
1. Create a handover with open incidents
2. Leave the "assigned to" field empty
3. Check that notifications appear in dashboard
4. Verify admin can see pending assignments in reports
