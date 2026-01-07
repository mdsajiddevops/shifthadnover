"""
Handover Upload Template Generator

This module generates Excel templates for bulk handover data upload.
Users can fill in the template and upload it to quickly create handover entries.
"""

import os
from openpyxl import Workbook
from openpyxl.styles import Font, Fill, PatternFill, Border, Side, Alignment, Protection
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.comments import Comment


def generate_handover_template(output_path=None):
    """
    Generate an Excel template for handover data upload.
    
    Args:
        output_path: Path where to save the template. If None, returns the workbook object.
    
    Returns:
        If output_path is None, returns the Workbook object.
        Otherwise, saves to the specified path and returns the path.
    """
    wb = Workbook()
    
    # Define styles
    header_font = Font(bold=True, color='FFFFFF', size=11)
    header_fill = PatternFill(start_color='2C5AA0', end_color='2C5AA0', fill_type='solid')
    section_fill = PatternFill(start_color='4A90E2', end_color='4A90E2', fill_type='solid')
    required_fill = PatternFill(start_color='FFE6E6', end_color='FFE6E6', fill_type='solid')
    optional_fill = PatternFill(start_color='E6F3FF', end_color='E6F3FF', fill_type='solid')
    example_fill = PatternFill(start_color='F5F5F5', end_color='F5F5F5', fill_type='solid')
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    center_align = Alignment(horizontal='center', vertical='center', wrap_text=True)
    left_align = Alignment(horizontal='left', vertical='center', wrap_text=True)
    
    # ==================== Sheet 1: Instructions ====================
    ws_instructions = wb.active
    ws_instructions.title = "Instructions"
    
    instructions = [
        ("SHIFT HANDOVER UPLOAD TEMPLATE", None),
        ("", None),
        ("HOW TO USE THIS TEMPLATE:", None),
        ("", None),
        ("1. Fill in the 'Basic Info' sheet with handover date, team, and shift details", None),
        ("2. Use the respective sheets to add incidents, changes, KB updates, and key points", None),
        ("3. Leave rows empty if you don't have data for that section", None),
        ("4. Save the file and upload it in the Handover Form page", None),
        ("", None),
        ("IMPORTANT NOTES:", None),
        ("", None),
        ("- Fields marked in RED are required", None),
        ("- Fields marked in BLUE are optional", None),
        ("- Use dropdown selections where available", None),
        ("- Dates should be in YYYY-MM-DD format", None),
        ("- Date-Time should be in YYYY-MM-DD HH:MM format", None),
        ("", None),
        ("SHEETS IN THIS TEMPLATE:", None),
        ("", None),
        ("1. Basic Info - Handover date, team, and shift information", None),
        ("2. Open Incidents - Active/Pending incidents to hand over", None),
        ("3. Closed Incidents - Incidents resolved during the shift", None),
        ("4. Priority Incidents - High priority/escalated incidents", None),
        ("5. Handover Incidents - Incidents requiring specific follow-up", None),
        ("6. Escalated Incidents - Incidents escalated to other teams/management", None),
        ("7. Change Info - Change requests during the shift", None),
        ("8. KB Updates - Knowledge base updates", None),
        ("9. Key Points - Important points for next shift", None),
        ("", None),
        ("For support, contact your team administrator.", None),
    ]
    
    for row_num, (text, _) in enumerate(instructions, 1):
        cell = ws_instructions.cell(row=row_num, column=1, value=text)
        if row_num == 1:
            cell.font = Font(bold=True, size=16, color='2C5AA0')
        elif text and text.endswith(':'):
            cell.font = Font(bold=True, size=12)
        elif text.startswith('- '):
            cell.font = Font(italic=True)
    
    ws_instructions.column_dimensions['A'].width = 80
    
    # ==================== Sheet 2: Basic Info ====================
    ws_basic = wb.create_sheet("Basic Info")
    
    basic_headers = [
        ("Field", "Value", "Description", "Required"),
        ("Handover Date", "", "Date of handover (YYYY-MM-DD)", "Yes"),
        ("Current Shift", "", "Morning/Evening/Late Evening/Night/General/OnShore/OffShore", "Yes"),
        ("Next Shift", "", "Morning/Evening/Late Evening/Night/General/OnShore/OffShore", "Yes"),
        ("Current Engineers", "", "Comma-separated names of current shift engineers", "No"),
        ("Next Engineers", "", "Comma-separated names of next shift engineers", "No"),
        ("Additional Notes", "", "Any additional notes for the handover", "No"),
    ]
    
    for row_num, (field, value, desc, req) in enumerate(basic_headers, 1):
        ws_basic.cell(row=row_num, column=1, value=field).border = thin_border
        ws_basic.cell(row=row_num, column=2, value=value).border = thin_border
        ws_basic.cell(row=row_num, column=3, value=desc).border = thin_border
        ws_basic.cell(row=row_num, column=4, value=req).border = thin_border
        
        if row_num == 1:
            for col in range(1, 5):
                cell = ws_basic.cell(row=row_num, column=col)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = center_align
        else:
            ws_basic.cell(row=row_num, column=1).font = Font(bold=True)
            ws_basic.cell(row=row_num, column=2).fill = required_fill if req == "Yes" else optional_fill
    
    # Add dropdown for shifts
    shift_validation = DataValidation(
        type="list",
        formula1='"Morning,Evening,Late Evening,Night,General,OnShore,OffShore"',
        allow_blank=True
    )
    ws_basic.add_data_validation(shift_validation)
    shift_validation.add('B3:B4')
    
    ws_basic.column_dimensions['A'].width = 20
    ws_basic.column_dimensions['B'].width = 40
    ws_basic.column_dimensions['C'].width = 50
    ws_basic.column_dimensions['D'].width = 12
    
    # ==================== Sheet 3: Open Incidents ====================
    ws_open = wb.create_sheet("Open Incidents")
    
    open_headers = ["Application Name", "Incident ID", "Priority", "Assigned To", "Description"]
    for col, header in enumerate(open_headers, 1):
        cell = ws_open.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.border = thin_border
        cell.alignment = center_align
    
    # Add example row
    example_data = ["MyApp", "INC0001234", "High", "John Doe", "Database connection timeout issue"]
    for col, value in enumerate(example_data, 1):
        cell = ws_open.cell(row=2, column=col, value=value)
        cell.fill = example_fill
        cell.border = thin_border
        cell.font = Font(italic=True, color='666666')
    
    # Add empty rows for data entry
    for row in range(3, 23):
        for col in range(1, 6):
            cell = ws_open.cell(row=row, column=col, value="")
            cell.border = thin_border
    
    # Priority dropdown
    priority_validation = DataValidation(
        type="list",
        formula1='"Low,Medium,High,Critical"',
        allow_blank=True
    )
    ws_open.add_data_validation(priority_validation)
    priority_validation.add('C2:C22')
    
    for col in range(1, 6):
        ws_open.column_dimensions[get_column_letter(col)].width = 25
    ws_open.column_dimensions['E'].width = 50
    
    # ==================== Sheet 4: Closed Incidents ====================
    ws_closed = wb.create_sheet("Closed Incidents")
    
    closed_headers = ["Application Name", "Incident ID", "Resolution Summary"]
    for col, header in enumerate(closed_headers, 1):
        cell = ws_closed.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.border = thin_border
        cell.alignment = center_align
    
    example_closed = ["PaymentGateway", "INC0005678", "Fixed by restarting the service and clearing cache"]
    for col, value in enumerate(example_closed, 1):
        cell = ws_closed.cell(row=2, column=col, value=value)
        cell.fill = example_fill
        cell.border = thin_border
        cell.font = Font(italic=True, color='666666')
    
    for row in range(3, 23):
        for col in range(1, 4):
            cell = ws_closed.cell(row=row, column=col, value="")
            cell.border = thin_border
    
    ws_closed.column_dimensions['A'].width = 25
    ws_closed.column_dimensions['B'].width = 20
    ws_closed.column_dimensions['C'].width = 60
    
    # ==================== Sheet 5: Priority Incidents ====================
    ws_priority = wb.create_sheet("Priority Incidents")
    
    priority_headers = ["Application Name", "Incident ID", "Priority Level", "Escalated To", "Impact & Actions"]
    for col, header in enumerate(priority_headers, 1):
        cell = ws_priority.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.border = thin_border
        cell.alignment = center_align
    
    example_priority = ["OrderSystem", "INC0009999", "Critical", "Manager - Alice", "Major revenue impact. Escalated to vendor."]
    for col, value in enumerate(example_priority, 1):
        cell = ws_priority.cell(row=2, column=col, value=value)
        cell.fill = example_fill
        cell.border = thin_border
        cell.font = Font(italic=True, color='666666')
    
    for row in range(3, 13):
        for col in range(1, 6):
            cell = ws_priority.cell(row=row, column=col, value="")
            cell.border = thin_border
    
    priority_level_validation = DataValidation(
        type="list",
        formula1='"High,Critical,Emergency"',
        allow_blank=True
    )
    ws_priority.add_data_validation(priority_level_validation)
    priority_level_validation.add('C2:C12')
    
    for col in range(1, 6):
        ws_priority.column_dimensions[get_column_letter(col)].width = 25
    ws_priority.column_dimensions['E'].width = 50
    
    # ==================== Sheet 6: Handover Incidents ====================
    ws_handover = wb.create_sheet("Handover Incidents")
    
    handover_headers = ["Application Name", "Incident ID", "Status", "Next Action By", "Notes & Next Actions"]
    for col, header in enumerate(handover_headers, 1):
        cell = ws_handover.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.border = thin_border
        cell.alignment = center_align
    
    example_handover = ["InventoryApp", "INC0007777", "Pending Vendor", "Jane Smith", "Waiting for vendor patch. Follow up at 10 AM."]
    for col, value in enumerate(example_handover, 1):
        cell = ws_handover.cell(row=2, column=col, value=value)
        cell.fill = example_fill
        cell.border = thin_border
        cell.font = Font(italic=True, color='666666')
    
    for row in range(3, 23):
        for col in range(1, 6):
            cell = ws_handover.cell(row=row, column=col, value="")
            cell.border = thin_border
    
    status_validation = DataValidation(
        type="list",
        formula1='"Monitoring,Pending Vendor,Pending Customer,In Progress,Waiting for Approval"',
        allow_blank=True
    )
    ws_handover.add_data_validation(status_validation)
    status_validation.add('C2:C22')
    
    for col in range(1, 6):
        ws_handover.column_dimensions[get_column_letter(col)].width = 25
    ws_handover.column_dimensions['E'].width = 50
    
    # ==================== Sheet 7: Escalated Incidents ====================
    ws_escalated = wb.create_sheet("Escalated Incidents")
    
    escalated_headers = ["Application Name", "Incident ID", "Escalated To", "Escalation Reason", "Status & Next Steps"]
    for col, header in enumerate(escalated_headers, 1):
        cell = ws_escalated.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.border = thin_border
        cell.alignment = center_align
    
    example_escalated = ["BillingSystem", "INC0003333", "Infrastructure Team", "Requires server upgrade", "Scheduled for weekend maintenance"]
    for col, value in enumerate(example_escalated, 1):
        cell = ws_escalated.cell(row=2, column=col, value=value)
        cell.fill = example_fill
        cell.border = thin_border
        cell.font = Font(italic=True, color='666666')
    
    for row in range(3, 13):
        for col in range(1, 6):
            cell = ws_escalated.cell(row=row, column=col, value="")
            cell.border = thin_border
    
    for col in range(1, 6):
        ws_escalated.column_dimensions[get_column_letter(col)].width = 25
    ws_escalated.column_dimensions['D'].width = 40
    ws_escalated.column_dimensions['E'].width = 40
    
    # ==================== Sheet 8: Change Info ====================
    ws_change = wb.create_sheet("Change Info")
    
    change_headers = ["Application Name", "Change Number", "Description", "Date Time", "Responsible Engineer", "Status"]
    for col, header in enumerate(change_headers, 1):
        cell = ws_change.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.border = thin_border
        cell.alignment = center_align
    
    example_change = ["WebPortal", "CHG0001234", "SSL Certificate renewal", "2025-01-15 14:00", "Bob Wilson", "Scheduled"]
    for col, value in enumerate(example_change, 1):
        cell = ws_change.cell(row=2, column=col, value=value)
        cell.fill = example_fill
        cell.border = thin_border
        cell.font = Font(italic=True, color='666666')
    
    for row in range(3, 18):
        for col in range(1, 7):
            cell = ws_change.cell(row=row, column=col, value="")
            cell.border = thin_border
    
    change_status_validation = DataValidation(
        type="list",
        formula1='"New,In Progress,Scheduled,Postponed,Completed,Cancelled"',
        allow_blank=True
    )
    ws_change.add_data_validation(change_status_validation)
    change_status_validation.add('F2:F17')
    
    ws_change.column_dimensions['A'].width = 20
    ws_change.column_dimensions['B'].width = 18
    ws_change.column_dimensions['C'].width = 40
    ws_change.column_dimensions['D'].width = 20
    ws_change.column_dimensions['E'].width = 22
    ws_change.column_dimensions['F'].width = 15
    
    # ==================== Sheet 9: KB Updates ====================
    ws_kb = wb.create_sheet("KB Updates")
    
    kb_headers = ["Application Name", "KB Number", "Description", "Responsible Person", "Status"]
    for col, header in enumerate(kb_headers, 1):
        cell = ws_kb.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.border = thin_border
        cell.alignment = center_align
    
    example_kb = ["HRPortal", "KB0001234", "Password reset procedure update", "Charlie Brown", "Published"]
    for col, value in enumerate(example_kb, 1):
        cell = ws_kb.cell(row=2, column=col, value=value)
        cell.fill = example_fill
        cell.border = thin_border
        cell.font = Font(italic=True, color='666666')
    
    for row in range(3, 13):
        for col in range(1, 6):
            cell = ws_kb.cell(row=row, column=col, value="")
            cell.border = thin_border
    
    kb_status_validation = DataValidation(
        type="list",
        formula1='"New,Draft,In Review,Published"',
        allow_blank=True
    )
    ws_kb.add_data_validation(kb_status_validation)
    kb_status_validation.add('E2:E12')
    
    ws_kb.column_dimensions['A'].width = 20
    ws_kb.column_dimensions['B'].width = 15
    ws_kb.column_dimensions['C'].width = 45
    ws_kb.column_dimensions['D'].width = 22
    ws_kb.column_dimensions['E'].width = 15
    
    # ==================== Sheet 10: Key Points ====================
    ws_keypoints = wb.create_sheet("Key Points")
    
    kp_headers = ["Key Point Details", "Assigned To", "Status"]
    for col, header in enumerate(kp_headers, 1):
        cell = ws_keypoints.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.border = thin_border
        cell.alignment = center_align
    
    example_kp = ["Monitor server CPU usage - spikes observed at peak hours", "David Lee", "Open"]
    for col, value in enumerate(example_kp, 1):
        cell = ws_keypoints.cell(row=2, column=col, value=value)
        cell.fill = example_fill
        cell.border = thin_border
        cell.font = Font(italic=True, color='666666')
    
    for row in range(3, 18):
        for col in range(1, 4):
            cell = ws_keypoints.cell(row=row, column=col, value="")
            cell.border = thin_border
    
    kp_status_validation = DataValidation(
        type="list",
        formula1='"Open,In Progress,Closed"',
        allow_blank=True
    )
    ws_keypoints.add_data_validation(kp_status_validation)
    kp_status_validation.add('C2:C17')
    
    ws_keypoints.column_dimensions['A'].width = 60
    ws_keypoints.column_dimensions['B'].width = 25
    ws_keypoints.column_dimensions['C'].width = 15
    
    # Save or return
    if output_path:
        wb.save(output_path)
        return output_path
    return wb


def generate_template_to_static():
    """Generate the template and save it to the static folder for download."""
    import os
    # Get the project root directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    
    # Create templates directory if it doesn't exist
    static_dir = os.path.join(project_root, 'static', 'templates')
    os.makedirs(static_dir, exist_ok=True)
    
    output_path = os.path.join(static_dir, 'handover_upload_template.xlsx')
    generate_handover_template(output_path)
    print(f"Template generated: {output_path}")
    return output_path


if __name__ == '__main__':
    generate_template_to_static()

