# SSO FIX FOR AUTH ROUTE
# Add this to your auth.py after successful authentication

def handle_first_time_user(user):
    """Handle first-time user login - redirect to onboarding if needed"""
    
    # Check if user needs onboarding
    if user.needs_onboarding:
        # Log the first-time user
        print(f"First-time user detected: {user.username}")
        
        # Set flash message
        flash('Welcome! Please complete your account setup to get started.', 'info')
        
        # Redirect to onboarding
        return redirect(url_for('onboarding.index'))
    
    # User already has account/team, proceed normally
    return redirect(url_for('dashboard.dashboard'))

# MODIFY YOUR LOGIN SUCCESS HANDLER TO USE THIS:
# After successful login, instead of direct redirect, use:
# return handle_first_time_user(current_user)
