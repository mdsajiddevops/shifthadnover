from flask import Blueprint, render_template

test_bp = Blueprint('test', __name__)

@test_bp.route('/test-js')
def test_js():
    """Test JavaScript functionality"""
    return render_template('test_js.html')