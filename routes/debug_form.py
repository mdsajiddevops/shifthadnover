from flask import Blueprint, request, jsonify
from flask_login import login_required
import json
import logging
logger = logging.getLogger(__name__)

debug_bp = Blueprint('debug', __name__)

@debug_bp.route('/debug/form', methods=['POST'])
@login_required  
def debug_form():
    """Capture and log exact form submission data"""
    
    logger.debug("=" * 50)
    logger.debug("DEBUG: FORM DATA CAPTURE")
    logger.debug("=" * 50)
    
    # Log all form fields
    logger.debug("Form fields:")
    for key, values in request.form.lists():
        logger.debug(f"  {key}: {values}")
        
    logger.debug("Form data (flat):")
    for key, value in request.form.items():
        logger.debug(f"  {key}: {repr(value)}")
        
    # Check for incident-related fields specifically
    logger.debug("Incident-related fields:")
    incident_fields = [k for k in request.form.keys() if 'incident' in k.lower()]
    for field in incident_fields:
        values = request.form.getlist(field)
        logger.debug(f"  {field}: {values}")
        
    logger.debug("=" * 50)
    
    return jsonify({
        "status": "logged",
        "form_keys": list(request.form.keys()),
        "incident_fields": incident_fields
    })