
# Enhanced User Management Route with Debugging
# Add this to your routes/user_management.py file

@user_mgmt_bp.route('/test-add-user', methods=['GET', 'POST'])
@login_required
def test_add_user():
    """Simplified test route for adding users"""
    if request.method == 'GET':
        # Serve the test form
        return send_file('test_user_form.html')
    
    if request.method == 'POST':
        print("=== TEST ADD USER DEBUG ===")
        print(f"Method: {request.method}")
        print(f"Form data: {dict(request.form)}")
        print(f"User: {current_user.username if hasattr(current_user, 'username') else 'Unknown'}")
        print(f"User role: {current_user.role if hasattr(current_user, 'role') else 'Unknown'}")
        
        try:
            username = request.form.get('username')
            password = request.form.get('password')
            role = request.form.get('role')
            account_id = request.form.get('account_id', type=int)
            first_name = request.form.get('first_name', '').strip()
            last_name = request.form.get('last_name', '').strip()
            
            print(f"Parsed data: username={username}, role={role}, account_id={account_id}")
            
            # Validation
            if not all([username, password, role, account_id]):
                error_msg = "Missing required fields"
                print(f"ERROR: {error_msg}")
                return f"ERROR: {error_msg}", 400
            
            # Check if user exists
            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                error_msg = "Username already exists"
                print(f"ERROR: {error_msg}")
                return f"ERROR: {error_msg}", 400
            
            # Check permissions
            if current_user.role not in ['super_admin', 'account_admin']:
                error_msg = "Permission denied"
                print(f"ERROR: {error_msg}")
                return f"ERROR: {error_msg}", 403
            
            # Create user
            user = User(
                username=username,
                password=generate_password_hash(password),
                role=role,
                account_id=account_id,
                team_id=None,
                status='active',
                is_active=True,
                first_name=first_name if first_name else None,
                last_name=last_name if last_name else None
            )
            
            db.session.add(user)
            db.session.flush()
            print(f"User created (before commit): id={user.id}, username={user.username}")
            
            db.session.commit()
            print(f"User successfully committed to database")
            
            return f"SUCCESS: User {username} created successfully with ID {user.id}", 200
            
        except Exception as e:
            db.session.rollback()
            error_msg = f"Exception occurred: {str(e)}"
            print(f"ERROR: {error_msg}")
            return f"ERROR: {error_msg}", 500

# Add debugging to existing route
def debug_user_management_post():
    """Add this debugging code to the main user_management route"""
    print("=== USER MANAGEMENT POST DEBUG ===")
    print(f"Request method: {request.method}")
    print(f"Content type: {request.content_type}")
    print(f"Form data: {dict(request.form)}")
    print(f"Request args: {dict(request.args)}")
    print(f"User authenticated: {current_user.is_authenticated}")
    print(f"User: {getattr(current_user, 'username', 'Unknown')}")
    print(f"User role: {getattr(current_user, 'role', 'Unknown')}")
    print("================================")
