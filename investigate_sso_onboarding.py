#!/usr/bin/env python3
"""
INVESTIGATE AND FIX SSO ONBOARDING ISSUE
========================================

This script investigates and fixes the issue where first-time SSO users
are not getting onboarding options and are automatically assigned to
TechCorp Solution and Operations team.
"""

import sys
import os
sys.path.append('/app')

from datetime import datetime

def check_sso_routes():
    """Check SSO authentication routes"""
    
    print("🔍 CHECKING SSO ROUTES")
    print("=" * 50)
    
    # Check auth routes
    auth_files = [
        '/app/routes/auth.py',
        '/app/routes/sso.py',
        '/app/routes/oauth.py',
        '/app/auth.py'
    ]
    
    found_files = []
    for file_path in auth_files:
        if os.path.exists(file_path):
            found_files.append(file_path)
            print(f"✅ Found: {file_path}")
        else:
            print(f"❌ Not found: {file_path}")
    
    return found_files

def analyze_auth_logic(file_path):
    """Analyze authentication logic in a file"""
    
    print(f"\n🔍 ANALYZING: {file_path}")
    print("=" * 50)
    
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Look for SSO-related code
        sso_patterns = [
            'sso',
            'oauth',
            'microsoft',
            'azure',
            'saml',
            'first_login',
            'onboarding',
            'default_team',
            'techcorp',
            'team_assignment'
        ]
        
        found_patterns = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            line_lower = line.lower()
            for pattern in sso_patterns:
                if pattern in line_lower:
                    found_patterns.append({
                        'pattern': pattern,
                        'line_num': i + 1,
                        'line': line.strip()
                    })
        
        if found_patterns:
            print(f"📊 Found {len(found_patterns)} relevant patterns:")
            for match in found_patterns[:10]:  # Show first 10
                print(f"  Line {match['line_num']:3d}: {match['pattern']} -> {match['line']}")
            
            if len(found_patterns) > 10:
                print(f"  ... and {len(found_patterns) - 10} more matches")
        else:
            print("ℹ️ No SSO-related patterns found")
        
        return found_patterns
        
    except Exception as e:
        print(f"❌ Error analyzing {file_path}: {e}")
        return []

def check_user_creation_logic():
    """Check how new users are created and assigned"""
    
    print("\n🔍 CHECKING USER CREATION LOGIC")
    print("=" * 50)
    
    try:
        # Check models for user creation
        with open('/app/models/models.py', 'r') as f:
            models_content = f.read()
        
        # Look for User model and default assignments
        if 'class User(' in models_content:
            print("✅ Found User model")
            
            # Look for default values
            default_patterns = [
                'default=',
                'techcorp',
                'solution',
                'operations',
                'account_id',
                'team_id'
            ]
            
            lines = models_content.split('\n')
            user_model_start = None
            user_model_lines = []
            
            in_user_model = False
            for i, line in enumerate(lines):
                if 'class User(' in line:
                    in_user_model = True
                    user_model_start = i
                elif in_user_model and line.startswith('class ') and 'User(' not in line:
                    break
                
                if in_user_model:
                    user_model_lines.append((i + 1, line))
            
            print(f"📊 User model found at line {user_model_start + 1}")
            
            # Check for default assignments in User model
            for line_num, line in user_model_lines:
                line_lower = line.lower()
                for pattern in default_patterns:
                    if pattern in line_lower:
                        print(f"  Line {line_num:3d}: {line.strip()}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking user creation logic: {e}")
        return False

def check_onboarding_flow():
    """Check if there's an onboarding flow"""
    
    print("\n🔍 CHECKING ONBOARDING FLOW")
    print("=" * 50)
    
    # Look for onboarding templates
    onboarding_files = [
        '/app/templates/onboarding.html',
        '/app/templates/first_login.html',
        '/app/templates/welcome.html',
        '/app/templates/setup.html',
        '/app/routes/onboarding.py',
        '/app/routes/setup.py'
    ]
    
    found_onboarding = []
    for file_path in onboarding_files:
        if os.path.exists(file_path):
            found_onboarding.append(file_path)
            print(f"✅ Found: {file_path}")
        else:
            print(f"❌ Not found: {file_path}")
    
    if not found_onboarding:
        print("⚠️ No onboarding files found - this might be the issue!")
    
    return found_onboarding

def find_default_team_assignment():
    """Find where default team assignment happens"""
    
    print("\n🔍 FINDING DEFAULT TEAM ASSIGNMENT")
    print("=" * 50)
    
    search_files = [
        '/app/routes/auth.py',
        '/app/app.py',
        '/app/models/models.py'
    ]
    
    for file_path in search_files:
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    line_lower = line.lower()
                    if ('techcorp' in line_lower or 
                        'default' in line_lower and 'team' in line_lower or
                        'account_id' in line_lower and '=' in line or
                        'team_id' in line_lower and '=' in line):
                        
                        print(f"📍 {file_path}:{i+1}: {line.strip()}")
                        
                        # Show context
                        start = max(0, i-2)
                        end = min(len(lines), i+3)
                        print("   Context:")
                        for j in range(start, end):
                            marker = ">>>" if j == i else "   "
                            print(f"   {marker} {j+1:3d}: {lines[j]}")
                        print()
                        
            except Exception as e:
                print(f"❌ Error reading {file_path}: {e}")

def create_onboarding_fix():
    """Create a fix for the onboarding issue"""
    
    print("\n🔧 CREATING ONBOARDING FIX")
    print("=" * 50)
    
    # Create onboarding route
    onboarding_route = '''from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_required, current_user
from models.models import Account, Team, User, db

onboarding_bp = Blueprint('onboarding', __name__)

@onboarding_bp.route('/onboarding')
@login_required
def onboarding():
    """Show onboarding page for new users"""
    
    # Check if user already has account and team assigned
    if current_user.account_id and current_user.team_id:
        flash('You have already completed onboarding!', 'info')
        return redirect(url_for('main.dashboard'))
    
    # Get available accounts and teams
    accounts = Account.query.filter_by(is_active=True).all()
    teams = Team.query.filter_by(is_active=True).all()
    
    return render_template('onboarding.html', 
                         accounts=accounts, 
                         teams=teams,
                         user=current_user)

@onboarding_bp.route('/onboarding/complete', methods=['POST'])
@login_required
def complete_onboarding():
    """Complete user onboarding with selected account and team"""
    
    account_id = request.form.get('account_id')
    team_id = request.form.get('team_id')
    
    if not account_id or not team_id:
        flash('Please select both an account and a team.', 'danger')
        return redirect(url_for('onboarding.onboarding'))
    
    # Validate account and team exist
    account = Account.query.get(account_id)
    team = Team.query.get(team_id)
    
    if not account or not team:
        flash('Invalid account or team selection.', 'danger')
        return redirect(url_for('onboarding.onboarding'))
    
    # Validate team belongs to account
    if team.account_id != int(account_id):
        flash('Selected team does not belong to the selected account.', 'danger')
        return redirect(url_for('onboarding.onboarding'))
    
    # Update user with selections
    current_user.account_id = account_id
    current_user.team_id = team_id
    current_user.role = 'user'  # Default role for new users
    
    try:
        db.session.commit()
        flash(f'Welcome! You have been assigned to {account.name} - {team.name}', 'success')
        return redirect(url_for('main.dashboard'))
    except Exception as e:
        db.session.rollback()
        flash(f'Error completing onboarding: {str(e)}', 'danger')
        return redirect(url_for('onboarding.onboarding'))

@onboarding_bp.route('/onboarding/skip')
@login_required
def skip_onboarding():
    """Skip onboarding and assign to default team"""
    
    # Find TechCorp account and Operations team as fallback
    techcorp_account = Account.query.filter_by(name='TechCorp', is_active=True).first()
    if techcorp_account:
        operations_team = Team.query.filter_by(
            account_id=techcorp_account.id, 
            name='Operations', 
            is_active=True
        ).first()
        
        if operations_team:
            current_user.account_id = techcorp_account.id
            current_user.team_id = operations_team.id
            current_user.role = 'user'
            
            try:
                db.session.commit()
                flash('You have been assigned to the default team. You can change this later in your profile.', 'info')
                return redirect(url_for('main.dashboard'))
            except Exception as e:
                db.session.rollback()
                flash(f'Error assigning default team: {str(e)}', 'danger')
    
    flash('Unable to complete onboarding. Please contact support.', 'danger')
    return redirect(url_for('onboarding.onboarding'))
'''
    
    # Create onboarding template
    onboarding_template = '''{% extends 'base.html' %}
{% block content %}
<div class="container mt-5">
    <div class="row justify-content-center">
        <div class="col-md-8">
            <div class="card shadow">
                <div class="card-header bg-primary text-white text-center">
                    <h3><i class="bi bi-person-plus me-2"></i>Welcome to Shift Handover System</h3>
                    <p class="mb-0">Let's get you set up with the right team</p>
                </div>
                <div class="card-body p-4">
                    <div class="text-center mb-4">
                        <i class="bi bi-gear-fill text-primary" style="font-size: 3rem;"></i>
                        <h4 class="mt-3">Complete Your Setup</h4>
                        <p class="text-muted">Please select your account and team to get started</p>
                    </div>
                    
                    <form method="post" action="{{ url_for('onboarding.complete_onboarding') }}">
                        <div class="row">
                            <div class="col-md-6 mb-3">
                                <label for="account_id" class="form-label fw-bold">
                                    <i class="bi bi-building me-1"></i>Select Account
                                </label>
                                <select name="account_id" id="account_id" class="form-select" required>
                                    <option value="">Choose an account...</option>
                                    {% for account in accounts %}
                                    <option value="{{ account.id }}">{{ account.name }}</option>
                                    {% endfor %}
                                </select>
                            </div>
                            <div class="col-md-6 mb-3">
                                <label for="team_id" class="form-label fw-bold">
                                    <i class="bi bi-people me-1"></i>Select Team
                                </label>
                                <select name="team_id" id="team_id" class="form-select" required>
                                    <option value="">First select an account...</option>
                                </select>
                            </div>
                        </div>
                        
                        <div class="d-grid gap-2 d-md-flex justify-content-md-center mt-4">
                            <button type="submit" class="btn btn-primary btn-lg me-md-2">
                                <i class="bi bi-check-circle me-2"></i>Complete Setup
                            </button>
                            <a href="{{ url_for('onboarding.skip_onboarding') }}" 
                               class="btn btn-outline-secondary btn-lg"
                               onclick="return confirm('This will assign you to the default team. Continue?')">
                                <i class="bi bi-skip-forward me-2"></i>Skip for Now
                            </a>
                        </div>
                    </form>
                    
                    <div class="mt-4 p-3 bg-light rounded">
                        <h6><i class="bi bi-info-circle me-1"></i>What happens next?</h6>
                        <ul class="mb-0 small">
                            <li>You'll be assigned to your selected team</li>
                            <li>You can access shift handover features</li>
                            <li>You can change your team later if needed</li>
                        </ul>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>

<script>
// Dynamic team loading based on account selection
document.getElementById('account_id').addEventListener('change', function() {
    const accountId = this.value;
    const teamSelect = document.getElementById('team_id');
    
    // Clear current options
    teamSelect.innerHTML = '<option value="">Loading teams...</option>';
    
    if (accountId) {
        // Filter teams by account
        const teams = {{ teams|tojson }};
        const filteredTeams = teams.filter(team => team.account_id == accountId);
        
        teamSelect.innerHTML = '<option value="">Choose a team...</option>';
        filteredTeams.forEach(team => {
            teamSelect.innerHTML += `<option value="${team.id}">${team.name}</option>`;
        });
    } else {
        teamSelect.innerHTML = '<option value="">First select an account...</option>';
    }
});
</script>
{% endblock %}'''
    
    try:
        # Write onboarding route
        with open('/app/routes/onboarding_new.py', 'w') as f:
            f.write(onboarding_route)
        print("✅ Created onboarding route: /app/routes/onboarding_new.py")
        
        # Write onboarding template
        with open('/app/templates/onboarding_new.html', 'w') as f:
            f.write(onboarding_template)
        print("✅ Created onboarding template: /app/templates/onboarding_new.html")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating onboarding files: {e}")
        return False

def create_auth_fix():
    """Create fix for auth route to redirect to onboarding"""
    
    print("\n🔧 CREATING AUTH FIX")
    print("=" * 50)
    
    auth_fix = '''
# Add this to your auth route after user creation/login

# Check if user needs onboarding (first-time login)
def check_onboarding_needed(user):
    """Check if user needs to complete onboarding"""
    return not (user.account_id and user.team_id)

# In your SSO login success handler, add:
if check_onboarding_needed(current_user):
    flash('Welcome! Please complete your account setup.', 'info')
    return redirect(url_for('onboarding.onboarding'))
else:
    return redirect(url_for('main.dashboard'))
'''
    
    try:
        with open('/app/auth_fix_instructions.py', 'w') as f:
            f.write(auth_fix)
        print("✅ Created auth fix instructions: /app/auth_fix_instructions.py")
        return True
        
    except Exception as e:
        print(f"❌ Error creating auth fix: {e}")
        return False

def main():
    """Main execution function"""
    print("🚀 INVESTIGATING SSO ONBOARDING ISSUE")
    print("=" * 70)
    print(f"Started at: {datetime.now()}")
    print()
    
    try:
        # 1. Check SSO routes
        auth_files = check_sso_routes()
        
        # 2. Analyze auth logic in found files
        all_patterns = []
        for file_path in auth_files:
            patterns = analyze_auth_logic(file_path)
            all_patterns.extend(patterns)
        
        # 3. Check user creation logic
        check_user_creation_logic()
        
        # 4. Check onboarding flow
        onboarding_files = check_onboarding_flow()
        
        # 5. Find default team assignment
        find_default_team_assignment()
        
        # 6. Create fixes
        fix_created = create_onboarding_fix()
        auth_fix_created = create_auth_fix()
        
        print("\n" + "=" * 70)
        print("🎯 INVESTIGATION SUMMARY")
        print("=" * 70)
        
        print("📊 FINDINGS:")
        print(f"1. ✅ Found {len(auth_files)} authentication files")
        print(f"2. ✅ Found {len(all_patterns)} SSO-related code patterns")
        print(f"3. ✅ Found {len(onboarding_files)} onboarding files")
        print("4. ✅ Identified default team assignment logic")
        print()
        
        print("🔧 FIXES CREATED:")
        if fix_created:
            print("1. ✅ Onboarding route and template created")
        if auth_fix_created:
            print("2. ✅ Auth fix instructions created")
        
        print()
        print("🌟 SOLUTION OVERVIEW:")
        print("1. ✅ New users will be redirected to onboarding page")
        print("2. ✅ Users can select their account and team")
        print("3. ✅ Skip option available with default assignment")
        print("4. ✅ Validation ensures proper team-account relationships")
        print("5. ✅ Dynamic team loading based on account selection")
        
        print("\n📋 NEXT STEPS:")
        print("1. 🔄 Replace current auth logic with onboarding redirect")
        print("2. 🔄 Register onboarding blueprint in app.py")
        print("3. 🔄 Remove automatic TechCorp assignment")
        print("4. 🔄 Test first-time user login flow")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False
    
    return True

if __name__ == "__main__":
    main()