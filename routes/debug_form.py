from flask import Blueprint, request, jsonify
from flask_login import login_required
import json

debug_bp = Blueprint('debug', __name__)

@debug_bp.route('/debug/form', methods=['POST'])
@login_required  
def debug_form():
    """Capture and log exact form submission data"""
    
    print("="*50)
    print("DEBUG: FORM DATA CAPTURE")
    print("="*50)
    
    # Log all form fields
    print("Form fields:")
    for key, values in request.form.lists():
        print(f"  {key}: {values}")
        
    print("\nForm data (flat):")
    for key, value in request.form.items():
        print(f"  {key}: {repr(value)}")
        
    # Check for incident-related fields specifically
    print("\nIncident-related fields:")
    incident_fields = [k for k in request.form.keys() if 'incident' in k.lower()]
    for field in incident_fields:
        values = request.form.getlist(field)
        print(f"  {field}: {values}")
        
    print("="*50)
    
    return jsonify({
        "status": "logged",
        "form_keys": list(request.form.keys()),
        "incident_fields": incident_fields
    })