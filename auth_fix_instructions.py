
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
