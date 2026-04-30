"""
SSO Authentication Routes
Handles Single Sign-On authentication flows for multiple providers
"""

from flask import Blueprint, request, redirect, url_for, flash, session, render_template, current_app
from flask_login import login_user, logout_user, current_user
from urllib.parse import urlparse, urljoin
import requests
import logging
from datetime import datetime
from models.models import db, User, Account, Team, TeamMember
from models.sso_config import SSOConfig

# Module logger
logger = logging.getLogger(__name__)
# Remove audit import for now - will use Flask logging instead
import xml.etree.ElementTree as ET
import base64
from cryptography.hazmat.primitives.serialization import load_pem_private_key
import hashlib
import secrets
import re
from difflib import SequenceMatcher
import logging

sso_auth = Blueprint('sso_auth', __name__, url_prefix='/auth/sso')

# Global variable to store last SSO claims for debugging
last_sso_claims = {}

@sso_auth.route('/debug/claims')
def debug_claims():
    """Debug endpoint to view last SSO claims received"""
    if not current_user.is_authenticated or current_user.role not in ['super_admin', 'account_admin']:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('auth.login'))
    
    return render_template('debug_sso_claims.html', claims=last_sso_claims)

@sso_auth.route('/initiate/<provider>')
def initiate_sso(provider):
    """Initiate SSO login for specified provider"""
    try:
        # Get account context if specified
        account_id = request.args.get('account_id')
        
        # Handle Google provider specifically
        if provider == 'oauth' and request.args.get('provider') == 'google':
            provider = 'google_oauth'
        
        # Check if provider is enabled
        if not SSOConfig.is_provider_enabled(provider, account_id):
            flash(f'SSO provider {provider} is not enabled', 'error')
            return redirect(url_for('auth.login'))
        
        # Get provider configuration
        config = SSOConfig.get_provider_config(provider, account_id)
        
        if provider == 'saml':
            return _initiate_saml_login(config, account_id)
        elif provider == 'azure_ad':
            return _initiate_azure_ad_login(config, account_id)
        elif provider in ['oauth', 'google_oauth']:
            return _initiate_oauth_login(config, account_id)
        else:
            flash(f'Unknown SSO provider: {provider}', 'error')
            return redirect(url_for('auth.login'))
            
    except Exception as e:
        current_app.logger.error(f"SSO initiation error for {provider}: {str(e)}")
        flash('SSO authentication failed. Please try again.', 'error')
        return redirect(url_for('auth.login'))

@sso_auth.route('/callback/<provider>', methods=['GET', 'POST'])
def sso_callback(provider):
    """Handle SSO callback from provider"""
    try:
        # Enhanced debugging for callback investigation
        current_app.logger.info(f"SSO callback for provider: {provider}")
        current_app.logger.info(f"Request method: {request.method}")
        current_app.logger.info(f"Request URL: {request.url}")
        current_app.logger.info(f"Request args: {dict(request.args)}")
        current_app.logger.info(f"Request form: {dict(request.form)}")
        current_app.logger.info(f"Request headers: {dict(request.headers)}")
        current_app.logger.info(f"Request query string: {request.query_string}")
        
        # Check for OAuth errors
        if request.args.get('error'):
            error = request.args.get('error')
            error_desc = request.args.get('error_description', '')
            current_app.logger.error(f"OAuth error: {error} - {error_desc}")
            flash(f'OAuth authentication failed: {error_desc}', 'error')
            return redirect(url_for('auth.login'))
        
        account_id = session.get('sso_account_id')
        
        # Handle Google OAuth callback
        if provider == 'oauth' and session.get('oauth_provider') == 'google':
            provider = 'google_oauth'
        
        if provider == 'saml':
            return _handle_saml_callback(account_id)
        elif provider == 'azure_ad':
            return _handle_azure_ad_callback(account_id)
        elif provider in ['oauth', 'google_oauth']:
            return _handle_oauth_callback(account_id)
        else:
            flash(f'Unknown SSO provider: {provider}', 'error')
            return redirect(url_for('auth.login'))
            
    except Exception as e:
        current_app.logger.error(f"SSO callback error for {provider}: {str(e)}")
        flash('SSO authentication failed. Please try again.', 'error')
        return redirect(url_for('auth.login'))

def _initiate_saml_login(config, account_id):
    """Initiate SAML 2.0 login"""
    # Store account context in session
    session['sso_account_id'] = account_id
    
    # Generate SAML request
    request_id = secrets.token_hex(16)
    session['saml_request_id'] = request_id
    
    saml_request = f"""
    <samlp:AuthnRequest
        xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
        xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
        ID="{request_id}"
        Version="2.0"
        IssueInstant="{datetime.utcnow().isoformat()}Z"
        AssertionConsumerServiceURL="{config.get('acs_url')}"
        Destination="{config.get('sso_url')}">
        <saml:Issuer>{config.get('entity_id')}</saml:Issuer>
    </samlp:AuthnRequest>
    """
    
    # Encode and redirect
    encoded_request = base64.b64encode(saml_request.encode()).decode()
    redirect_url = f"{config.get('sso_url')}?SAMLRequest={encoded_request}"
    
    return redirect(redirect_url)

def _initiate_azure_ad_login(config, account_id):
    """Initiate Azure AD OAuth login"""
    session['sso_account_id'] = account_id
    
    # Generate state parameter for security
    state = secrets.token_hex(16)
    session['oauth_state'] = state
    
    # Build authorization URL
    params = {
        'client_id': config.get('client_id'),
        'response_type': 'code',
        'redirect_uri': config.get('redirect_uri'),
        'response_mode': 'query',
        'scope': 'openid profile email',
        'state': state
    }
    
    auth_url = config.get('auth_endpoint')
    query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
    redirect_url = f"{auth_url}?{query_string}"
    
    return redirect(redirect_url)

def _initiate_oauth_login(config, account_id):
    """Initiate generic OAuth 2.0 login"""
    from urllib.parse import urlencode, quote_plus
    
    session['sso_account_id'] = account_id
    
    # Store provider type for callback handling
    if 'accounts.google.com' in config.get('authorization_endpoint', ''):
        session['oauth_provider'] = 'google'
    
    # Generate state parameter
    state = secrets.token_hex(16)
    session['oauth_state'] = state
    
    # Build authorization URL with proper URL encoding
    params = {
        'client_id': config.get('client_id'),
        'response_type': 'code',
        'redirect_uri': config.get('redirect_uri'),
        'scope': config.get('scope', 'openid profile email'),
        'state': state
    }
    
    auth_url = config.get('authorization_endpoint')
    
    # Use proper URL encoding for query parameters
    query_string = urlencode(params)
    redirect_url = f"{auth_url}?{query_string}"
    
    # Debug logging
    current_app.logger.info(f"OAuth redirect URL: {redirect_url}")
    current_app.logger.info(f"Client ID: {config.get('client_id')}")
    current_app.logger.info(f"Redirect URI: {config.get('redirect_uri')}")
    current_app.logger.info(f"Authorization endpoint: {auth_url}")
    
    return redirect(redirect_url)

def _handle_saml_callback(account_id):
    """Handle SAML assertion callback"""
    saml_response = request.form.get('SAMLResponse')
    if not saml_response:
        flash('Invalid SAML response', 'error')
        return redirect(url_for('auth.login'))
    
    # Decode and parse SAML response
    decoded_response = base64.b64decode(saml_response).decode()
    root = ET.fromstring(decoded_response)
    
    # Extract user attributes (simplified - in production, validate signature!)
    attributes = {}
    for attribute in root.findall('.//{urn:oasis:names:tc:SAML:2.0:assertion}Attribute'):
        name = attribute.get('Name')
        value = attribute.find('.//{urn:oasis:names:tc:SAML:2.0:assertion}AttributeValue').text
        attributes[name] = value
    
    # ====== DETAILED SAML CLAIMS LOGGING ======
    current_app.logger.info("=" * 60)
    current_app.logger.info("🔍 SAML ASSERTION CLAIMS ANALYSIS")
    current_app.logger.info("=" * 60)
    current_app.logger.info(f"📊 Total number of SAML attributes received: {len(attributes)}")
    current_app.logger.info(f"🔑 Available SAML attribute names: {list(attributes.keys())}")
    
    # Log all SAML attributes
    for name, value in attributes.items():
        value_str = str(value)
        if len(value_str) > 100:
            value_str = value_str[:100] + "... (truncated)"
        current_app.logger.info(f"  📋 {name}: {value_str}")
    
    current_app.logger.info("=" * 60)
    current_app.logger.info("END SAML CLAIMS ANALYSIS")
    current_app.logger.info("=" * 60)
    
    # Map SAML attributes to user data
    user_data = {
        'email': attributes.get('http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress'),
        'first_name': attributes.get('http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname'),
        'last_name': attributes.get('http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname'),
        'username': attributes.get('http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name')
    }
    
    return _process_sso_user(user_data, 'saml', account_id)

def _handle_azure_ad_callback(account_id):
    """Handle Azure AD OAuth callback"""
    code = request.args.get('code')
    state = request.args.get('state')
    
    # Verify state parameter
    if state != session.get('oauth_state'):
        flash('Invalid OAuth state', 'error')
        return redirect(url_for('auth.login'))
    
    # Get provider configuration
    config = SSOConfig.get_provider_config('azure_ad', account_id)
    
    # Exchange code for token
    token_data = {
        'client_id': config.get('client_id'),
        'client_secret': config.get('client_secret'),
        'code': code,
        'grant_type': 'authorization_code',
        'redirect_uri': config.get('redirect_uri')
    }
    
    token_response = requests.post(config.get('token_endpoint'), data=token_data)
    token_json = token_response.json()
    
    if 'access_token' not in token_json:
        flash('Failed to obtain access token', 'error')
        return redirect(url_for('auth.login'))
    
    # Get user info
    headers = {'Authorization': f"Bearer {token_json['access_token']}"}
    user_response = requests.get(config.get('userinfo_endpoint'), headers=headers)
    user_data = user_response.json()
    
    # ====== DETAILED AZURE AD CLAIMS LOGGING ======
    current_app.logger.info("=" * 60)
    current_app.logger.info("🔍 AZURE AD CLAIMS ANALYSIS")
    current_app.logger.info("=" * 60)
    current_app.logger.info(f"📊 Total number of claims received: {len(user_data)}")
    current_app.logger.info(f"🔑 Available claim keys: {list(user_data.keys())}")
    
    # Log all claims with their values
    for key, value in user_data.items():
        value_str = str(value)
        if len(value_str) > 100:
            value_str = value_str[:100] + "... (truncated)"
        current_app.logger.info(f"  📋 {key}: {value_str}")
    
    # Azure AD specific claims
    azure_claims = [
        'oid', 'tid', 'upn', 'unique_name', 'given_name', 'family_name', 'name',
        'email', 'preferred_username', 'jobTitle', 'department', 'companyName',
        'streetAddress', 'city', 'state', 'postalCode', 'country'
    ]
    
    current_app.logger.info("\n🎯 AZURE AD SPECIFIC CLAIMS STATUS:")
    for claim in azure_claims:
        status = "✅ Present" if claim in user_data else "❌ Missing"
        value = user_data.get(claim, 'N/A')
        if isinstance(value, str) and len(value) > 50:
            value = value[:50] + "..."
        current_app.logger.info(f"  {claim}: {status} - {value}")
    
    current_app.logger.info("=" * 60)
    current_app.logger.info("END AZURE AD CLAIMS ANALYSIS")
    current_app.logger.info("=" * 60)
    
    return _process_sso_user(user_data, 'azure_ad', account_id)

def _handle_oauth_callback(account_id):
    """Handle generic OAuth callback"""
    code = request.args.get('code')
    state = request.args.get('state')
    
    current_app.logger.info(f"OAuth callback - Code: {code[:10] if code else 'None'}...")
    current_app.logger.info(f"OAuth callback - State: {state}")
    
    # Verify state parameter
    if state != session.get('oauth_state'):
        flash('Invalid OAuth state', 'error')
        return redirect(url_for('auth.login'))
    
    # Get provider configuration
    config = SSOConfig.get_provider_config('oauth', account_id)
    
    # Debug client secret decryption issue
    client_secret = config.get('client_secret')
    current_app.logger.info(f"Raw client secret from config: {client_secret}")
    
    # Fix decryption issue - manually decrypt if needed
    if client_secret and client_secret.startswith('gAAAA'):
        current_app.logger.warning("Client secret appears to still be encrypted, attempting manual decryption...")
        try:
            # Get the raw config from database and decrypt manually
            from models.sso_config import SSOConfig as SSOConfigModel
            secret_config = SSOConfigModel.query.filter_by(
                provider_type='oauth',
                config_key='client_secret'
            ).first()
            
            if secret_config and secret_config.encrypted:
                # Try to decrypt using the model's decrypt method
                decrypted_secret = SSOConfigModel._decrypt_value(secret_config.config_value)
                config['client_secret'] = decrypted_secret
                current_app.logger.info(f"✅ Successfully manually decrypted client secret, length: {len(decrypted_secret) if decrypted_secret else 0}")
            else:
                current_app.logger.error("❌ Client secret config not found or not marked as encrypted")
        except Exception as decrypt_error:
            current_app.logger.error(f"❌ Manual decryption failed: {decrypt_error}")
            # Try using it as-is (maybe it's already decrypted but showing encrypted format)
    
    # Debug: Log configuration details
    current_app.logger.info(f"Token endpoint: {config.get('token_endpoint')}")
    current_app.logger.info(f"Client ID: {config.get('client_id')}")
    current_app.logger.info(f"Redirect URI: {config.get('redirect_uri')}")
    
    # Exchange code for token
    token_data = {
        'code': code,
        'grant_type': 'authorization_code',
        'redirect_uri': config.get('redirect_uri')
    }
    
    try:
        current_app.logger.info(f"Making token request to: {config.get('token_endpoint')}")
        
        # Try basic authentication first (common for Keycloak)
        auth = (config.get('client_id'), config.get('client_secret'))
        client_secret = config.get('client_secret')
        current_app.logger.info(f"Using basic auth with client_id: {config.get('client_id')}")
        current_app.logger.info(f"Client secret length: {len(client_secret) if client_secret else 0}")
        current_app.logger.info(f"Client secret starts with: {client_secret[:5] if client_secret and len(client_secret) > 5 else 'EMPTY'}")
        
        token_response = requests.post(
            config.get('token_endpoint'), 
            data=token_data, 
            auth=auth,
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            timeout=30
        )
        
        current_app.logger.info(f"Token response status: {token_response.status_code}")
        current_app.logger.info(f"Token response headers: {dict(token_response.headers)}")
        
        if token_response.status_code != 200:
            current_app.logger.error(f"Basic auth failed, trying form data method...")
            
            # Fallback to form data method
            token_data_with_creds = {
                'client_id': config.get('client_id'),
                'client_secret': config.get('client_secret'),
                'code': code,
                'grant_type': 'authorization_code',
                'redirect_uri': config.get('redirect_uri')
            }
            
            token_response = requests.post(
                config.get('token_endpoint'), 
                data=token_data_with_creds,
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=30
            )
            current_app.logger.info(f"Form data method - Token response status: {token_response.status_code}")
        
        if token_response.status_code != 200:
            current_app.logger.error(f"Token request failed with status {token_response.status_code}")
            current_app.logger.error(f"Token response text: {token_response.text}")
            flash(f'Failed to obtain access token: {token_response.json().get("error_description", "Invalid credentials")}', 'error')
            return redirect(url_for('auth.login'))
        
        token_json = token_response.json()
        current_app.logger.info(f"Token response keys: {list(token_json.keys())}")
        
        if 'access_token' not in token_json:
            current_app.logger.error(f"No access_token in response: {token_json}")
            flash('Failed to obtain access token', 'error')
            return redirect(url_for('auth.login'))
        
        current_app.logger.info("Access token obtained successfully")
        
        # Get user info
        headers = {'Authorization': f"Bearer {token_json['access_token']}"}
        current_app.logger.info(f"Making userinfo request to: {config.get('userinfo_endpoint')}")
        user_response = requests.get(config.get('userinfo_endpoint'), headers=headers, timeout=30)
        current_app.logger.info(f"Userinfo response status: {user_response.status_code}")
        
        if user_response.status_code != 200:
            current_app.logger.error(f"Userinfo request failed with status {user_response.status_code}")
            current_app.logger.error(f"Userinfo response text: {user_response.text}")
            flash(f'Failed to get user information: HTTP {user_response.status_code}', 'error')
            return redirect(url_for('auth.login'))
        
        user_data = user_response.json()
        
        # ====== DETAILED OAUTH CLAIMS LOGGING ======
        current_app.logger.info("=" * 60)
        current_app.logger.info("🔍 OAUTH SERVER CLAIMS ANALYSIS")
        current_app.logger.info("=" * 60)
        current_app.logger.info(f"📊 Total number of claims received: {len(user_data)}")
        current_app.logger.info(f"🔑 Available claim keys: {list(user_data.keys())}")
        
        # Log all claims with their values
        for key, value in user_data.items():
            value_str = str(value)
            if len(value_str) > 100:
                value_str = value_str[:100] + "... (truncated)"
            current_app.logger.info(f"  📋 {key}: {value_str}")
        
        # Standard OAuth claims check
        standard_claims = [
            'sub', 'email', 'email_verified', 'name', 'given_name', 'family_name',
            'preferred_username', 'picture', 'profile', 'locale', 'updated_at',
            'zoneinfo', 'nickname', 'website', 'gender', 'birthdate', 'phone_number',
            'phone_number_verified', 'address'
        ]
        
        current_app.logger.info("\n🎯 STANDARD OAUTH CLAIMS STATUS:")
        for claim in standard_claims:
            status = "✅ Present" if claim in user_data else "❌ Missing"
            value = user_data.get(claim, 'N/A')
            if isinstance(value, str) and len(value) > 50:
                value = value[:50] + "..."
            current_app.logger.info(f"  {claim}: {status} - {value}")
        
        # Custom/extended claims
        custom_claims = [k for k in user_data.keys() if k not in standard_claims]
        if custom_claims:
            current_app.logger.info(f"\n🔧 CUSTOM/EXTENDED CLAIMS ({len(custom_claims)}):")
            for claim in custom_claims:
                value = user_data.get(claim, 'N/A')
                if isinstance(value, str) and len(value) > 50:
                    value = value[:50] + "..."
                current_app.logger.info(f"  {claim}: {value}")
        else:
            current_app.logger.info("\n🔧 No custom claims found")
        
        # Security-related claims
        security_claims = ['iss', 'aud', 'exp', 'iat', 'auth_time', 'nonce', 'acr', 'amr', 'azp']
        security_present = [c for c in security_claims if c in user_data]
        if security_present:
            current_app.logger.info(f"\n🔒 SECURITY CLAIMS ({len(security_present)}):")
            for claim in security_present:
                current_app.logger.info(f"  {claim}: {user_data[claim]}")
        
        # Role/permission claims
        role_claims = ['roles', 'groups', 'authorities', 'permissions', 'scopes', 'realm_access', 'resource_access']
        role_present = [c for c in role_claims if c in user_data]
        if role_present:
            current_app.logger.info(f"\n👤 ROLE/PERMISSION CLAIMS ({len(role_present)}):")
            for claim in role_present:
                value = user_data[claim]
                current_app.logger.info(f"  {claim}: {value}")
        
        current_app.logger.info("=" * 60)
        current_app.logger.info("END OAUTH CLAIMS ANALYSIS")
        current_app.logger.info("=" * 60)
        
        current_app.logger.info(f"User email: {user_data.get('email', 'Not found')}")
        
        return _process_sso_user(user_data, 'oauth', account_id)
        
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Network error during token exchange: {str(e)}")
        flash('Network error during authentication. Please try again.', 'error')
        return redirect(url_for('auth.login'))
    except Exception as e:
        current_app.logger.error(f"Unexpected error during token exchange: {str(e)}")
        flash('Authentication error. Please try again.', 'error')
        return redirect(url_for('auth.login'))

def _process_sso_user(user_data, provider_type, account_id):
    """Process SSO user data and create/login user"""
    global last_sso_claims
    
    try:
        # Store claims for debugging
        last_sso_claims = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'provider_type': provider_type,
            'account_id': account_id,
            'user_data': user_data,
            'claims_count': len(user_data),
            'available_keys': list(user_data.keys())
        }
        
        # ====== DETAILED USER DATA PROCESSING LOGGING ======
        current_app.logger.info("=" * 60)
        current_app.logger.info("🔍 SSO USER DATA PROCESSING")
        current_app.logger.info("=" * 60)
        current_app.logger.info(f"🔧 Provider type: {provider_type}")
        current_app.logger.info(f"🏢 Account ID: {account_id}")
        current_app.logger.info(f"📊 User data received: {len(user_data)} fields")
        
        # Show how we're extracting key fields
        email_candidates = ['email', 'mail', 'preferred_username']
        current_app.logger.info("\n📧 EMAIL EXTRACTION PROCESS:")
        for candidate in email_candidates:
            value = user_data.get(candidate)
            current_app.logger.info(f"  {candidate}: {value if value else '❌ Not found'}")
        
        # Extract email (primary identifier)
        email = user_data.get('email') or user_data.get('mail') or user_data.get('preferred_username')
        current_app.logger.info(f"✅ Final extracted email: {email}")
        
        if not email:
            current_app.logger.error("❌ NO EMAIL FOUND IN SSO RESPONSE")
            flash('No email found in SSO response', 'error')
            return redirect(url_for('auth.login'))
        
        # Show name extraction process - prioritize given_name and family_name
        current_app.logger.info("\n👤 NAME EXTRACTION PROCESS (PRIORITIZED):")
        first_name = (user_data.get('given_name') or 
                     user_data.get('first_name') or 
                     user_data.get('givenName'))
        last_name = (user_data.get('family_name') or 
                    user_data.get('last_name') or 
                    user_data.get('surname'))
        full_name = user_data.get('name')
        username = user_data.get('preferred_username') or user_data.get('username') or email.split('@')[0]
        
        current_app.logger.info(f"  ✅ First Name: {first_name} (source: {_get_claim_source(user_data, ['given_name', 'first_name', 'givenName'])})")
        current_app.logger.info(f"  ✅ Last Name: {last_name} (source: {_get_claim_source(user_data, ['family_name', 'last_name', 'surname'])})")
        current_app.logger.info(f"  📝 Full Name: {full_name}")
        current_app.logger.info(f"  🔖 Username: {username}")
        
        # Show profile picture extraction - prioritize 'picture' claim
        current_app.logger.info("\n🖼️ PROFILE PICTURE EXTRACTION (PRIORITIZED):")
        picture = (user_data.get('picture') or 
                  user_data.get('avatar') or 
                  user_data.get('photo') or
                  user_data.get('avatar_url'))
        current_app.logger.info(f"  ✅ Picture URL: {picture} (source: {_get_claim_source(user_data, ['picture', 'avatar', 'photo', 'avatar_url'])})")
        
        current_app.logger.info("=" * 60)
        
        # Check if user exists
        user = User.query.filter_by(email=email).first()
        
        if not user:
            # Auto-provision user if enabled
            config = SSOConfig.get_provider_config(provider_type, account_id)
            if config.get('auto_provision') == 'true':
                user = _create_sso_user(user_data, provider_type, account_id)
            else:
                flash('User not found and auto-provisioning is disabled', 'error')
                return redirect(url_for('auth.login'))
        
        # Update user info from SSO
        _update_user_from_sso(user, user_data)
        
        # Check if existing user needs team member linking
        existing_link = TeamMember.query.filter_by(user_id=user.id).first()
        if not existing_link:
            current_app.logger.info(f"🔍 SSO Auto-Link: Existing user {user.email} not linked to team member, attempting auto-link...")
            
            # Extract data for linking
            sso_username = user_data.get('username') or user_data.get('preferred_username') or user.username
            full_name = f"{user.first_name} {user.last_name}".strip() if user.first_name or user.last_name else None
            
            success, team_member, confidence, reason = _auto_link_team_member(
                user, user.email, full_name, sso_username, min_confidence=70
            )
            
            if success and team_member:
                current_app.logger.info(f"🎉 SSO Auto-Link SUCCESS: Existing user {user.email} auto-linked to '{team_member.name}'")
                flash(f'Welcome back! You have been automatically linked to team member: {team_member.name}', 'success')
        
        # Update last login time for all users
        user.last_login = datetime.now()
        user.first_login = False
        db.session.commit()
        
        # Log the user in
        login_user(user)
        
        # Create session token for session management
        from routes.auth import create_user_session
        create_user_session(user)
        
        # Log SSO authentication
        current_app.logger.info(f'SSO login successful for user {user.email} via {provider_type}')
        
        # Super admin users bypass onboarding
        if user.role == 'super_admin':
            user.onboarding_completed = True
            db.session.commit()
            
            next_page = request.args.get('next')
            if not next_page or urlparse(next_page).netloc != '':
                next_page = url_for('dashboard.dashboard')
            return redirect(next_page)
        
        # Check if user needs onboarding (first-time login or no account/team assigned)
        if user.needs_onboarding:
            flash('Welcome! Please select your account and team to continue.', 'info')
            return redirect(url_for('onboarding.index'))
        
        # Handle account/team selection for multi-tenant users with existing assignments
        if user.role in ['account_admin', 'team_admin', 'user']:
            return _handle_account_team_selection(user, account_id)
        
        # Fallback redirect
        next_page = request.args.get('next')
        if not next_page or urlparse(next_page).netloc != '':
            next_page = url_for('dashboard.dashboard')
        
        return redirect(next_page)
        
    except Exception as e:
        current_app.logger.error(f"SSO user processing error: {str(e)}")
        flash('SSO authentication failed. Please try again.', 'error')
        return redirect(url_for('auth.login'))

def _get_claim_source(user_data, claim_keys):
    """Helper function to identify which claim key was used"""
    for key in claim_keys:
        if user_data.get(key):
            return key
    return "none"

def _create_sso_user(user_data, provider_type, account_id):
    """Create new user from SSO data"""
    email = user_data.get('email') or user_data.get('mail') or user_data.get('preferred_username')
    
    # Extract name components - prioritize given_name and family_name from SSO claims
    first_name = (user_data.get('given_name') or 
                 user_data.get('first_name') or 
                 user_data.get('givenName', ''))
    last_name = (user_data.get('family_name') or 
                user_data.get('last_name') or 
                user_data.get('surname', ''))
    
    # Extract profile picture - prioritize 'picture' claim from SSO
    profile_picture = (user_data.get('picture') or 
                      user_data.get('avatar_url') or 
                      user_data.get('photo'))
    
    # Log what we're using for the profile
    current_app.logger.info(f"🔍 SSO USER CREATION - Profile Data:")
    current_app.logger.info(f"  📧 Email: {email}")
    current_app.logger.info(f"  👤 First Name: {first_name} (from: {_get_claim_source(user_data, ['given_name', 'first_name', 'givenName'])})")
    current_app.logger.info(f"  👤 Last Name: {last_name} (from: {_get_claim_source(user_data, ['family_name', 'last_name', 'surname'])})")
    current_app.logger.info(f"  🖼️ Profile Picture: {profile_picture} (from: {_get_claim_source(user_data, ['picture', 'avatar_url', 'photo'])})")
    
    # Generate username from email if not provided
    username = user_data.get('username') or user_data.get('preferred_username') or email.split('@')[0]
    
    # Determine default role
    config = SSOConfig.get_provider_config(provider_type, account_id)
    default_role = config.get('default_role', 'user')
    
    # Create user (matching actual User model fields)
    user = User(
        username=username,
        email=email,
        first_name=first_name,
        last_name=last_name,
        profile_picture=profile_picture,
        role=default_role,
        account_id=account_id if default_role in ['account_admin', 'team_admin', 'user'] else None,
        team_id=None,  # Will be set during team selection
        is_active=True,
        password='',  # SSO users don't have local passwords
        status='active'
    )
    
    db.session.add(user)
    db.session.commit()
    
    current_app.logger.info(f"✅ Created new SSO user: {email} ({first_name} {last_name}) via {provider_type}")
    
    # Enhanced automatic team member linking using our new service
    current_app.logger.info(f"🔍 SSO Auto-Link: Attempting to link {email} to existing team member...")
    
    try:
        # Import the enhanced linking service
        import sys
        sys.path.append('/app')
        from user_linking_service import UserTeamMemberLinkingService
        
        # Try automatic linking with high confidence for email matches
        success, team_member, confidence, message = UserTeamMemberLinkingService.link_user_to_teammember(
            user.id, auto_link=True
        )
        
        if success and team_member:
            current_app.logger.info(f"🎉 SSO Auto-Link SUCCESS: {message}")
            flash(f'Welcome! You have been automatically linked to team member: {team_member.name}', 'success')
            
            # Update user's team info from the linked team member
            if not user.team_id and team_member.team_id:
                user.team_id = team_member.team_id
            if not user.account_id and team_member.account_id:
                user.account_id = team_member.account_id
            db.session.commit()
            
        else:
            # Fallback: Try the existing auto-link method
            current_app.logger.info(f"🔄 SSO Fallback: Using existing auto-link method...")
            
            # Extract username for pattern matching
            sso_username = user_data.get('username') or user_data.get('preferred_username') or username
            full_name = f"{first_name} {last_name}".strip() if first_name or last_name else None
            
            success, team_member, confidence, reason = _auto_link_team_member(
                user, email, full_name, sso_username, min_confidence=70
            )
            
            if success and team_member:
                current_app.logger.info(f"🎉 SSO Fallback SUCCESS: User {email} linked to TeamMember '{team_member.name}' (ID: {team_member.id})")
                flash(f'Welcome! You have been automatically linked to team member: {team_member.name}', 'success')
            elif team_member and confidence >= 50:
                current_app.logger.info(f"⚠️ SSO Potential Match: User {email} has potential match '{team_member.name}' ({confidence}%) - flagged for manual review")
                flash(f'Account created. Potential team match found: {team_member.name} ({confidence}% confidence). Please contact admin to confirm linking.', 'info')
            else:
                # Last resort: Create a new TeamMember for this user
                current_app.logger.info(f"🏢 SSO Creating TeamMember: No existing match found for {email}, creating new TeamMember...")
                
                try:
                    tm_success, tm, tm_message = UserTeamMemberLinkingService.create_teammember_for_user(
                        user.id, team_id=2, account_id=account_id  # Default to Operations Team
                    )
                    
                    if tm_success:
                        current_app.logger.info(f"✅ SSO TeamMember Created: {tm_message}")
                        flash('Welcome! You have been assigned to the Operations Team. Please contact admin if you need to be moved to a different team.', 'success')
                    else:
                        current_app.logger.warning(f"⚠️ SSO TeamMember Creation Failed: {tm_message}")
                        flash('Account created. Please contact admin to assign you to a team for full access.', 'info')
                        
                except Exception as create_error:
                    current_app.logger.error(f"❌ SSO TeamMember Creation Error: {str(create_error)}")
                    flash('Account created. Please contact admin to assign you to a team for full access.', 'info')
                
    except Exception as e:
        current_app.logger.error(f"❌ SSO Auto-Link Error: {str(e)}")
        
        # Fallback to existing method if new service fails
        current_app.logger.info(f"🔄 SSO Emergency Fallback: Using existing auto-link method...")
        
        try:
            sso_username = user_data.get('username') or user_data.get('preferred_username') or username
            full_name = f"{first_name} {last_name}".strip() if first_name or last_name else None
            
            success, team_member, confidence, reason = _auto_link_team_member(
                user, email, full_name, sso_username, min_confidence=70
            )
            
            if success and team_member:
                flash(f'Welcome! You have been automatically linked to team member: {team_member.name}', 'success')
            else:
                flash('Account created. Please contact admin to link your account to a team member for full access.', 'info')
                
        except Exception as fallback_error:
            current_app.logger.error(f"❌ SSO Fallback Error: {str(fallback_error)}")
            flash('Account created. Please contact admin to link your account to a team member for full access.', 'info')
    
    return user

def _update_user_from_sso(user, user_data):
    """Update existing user with fresh SSO data"""
    # Update user status to active in case it was disabled
    user.is_active = True
    user.status = 'active'
    
    # Update name fields from SSO data - prioritize given_name and family_name
    first_name = (user_data.get('given_name') or 
                 user_data.get('first_name') or 
                 user_data.get('givenName', ''))
    last_name = (user_data.get('family_name') or 
                user_data.get('last_name') or 
                user_data.get('surname', ''))
    profile_picture = (user_data.get('picture') or 
                      user_data.get('avatar_url') or 
                      user_data.get('photo'))
    
    # Log what we're updating for the profile
    current_app.logger.info(f"🔄 SSO USER UPDATE - Profile Data:")
    current_app.logger.info(f"  📧 Email: {user.email}")
    current_app.logger.info(f"  👤 First Name: {first_name} (from: {_get_claim_source(user_data, ['given_name', 'first_name', 'givenName'])})")
    current_app.logger.info(f"  👤 Last Name: {last_name} (from: {_get_claim_source(user_data, ['family_name', 'last_name', 'surname'])})")
    current_app.logger.info(f"  🖼️ Profile Picture: {profile_picture} (from: {_get_claim_source(user_data, ['picture', 'avatar_url', 'photo'])})")
    
    # Update fields if they have values
    if first_name:
        user.first_name = first_name
    if last_name:
        user.last_name = last_name
    if profile_picture:
        user.profile_picture = profile_picture
    
    db.session.commit()
    current_app.logger.info(f"✅ Updated SSO user profile: {user.email} ({user.first_name} {user.last_name})")

def _handle_account_team_selection(user, account_id):
    """Handle account and team selection for multi-tenant SSO users"""
    # If account_id was specified in SSO initiation, use it
    if account_id and user.role in ['account_admin', 'team_admin', 'user']:
        account = Account.query.get(account_id)
        if account and (user.role == 'account_admin' or user.account_id == account_id):
            session['selected_account_id'] = account_id
            
            # For team roles, redirect to dashboard (team selection not implemented)
            if user.role in ['team_admin', 'user']:
                return redirect(url_for('dashboard.dashboard'))
            else:
                return redirect(url_for('dashboard.dashboard'))
    
    # Otherwise, redirect to dashboard (account selection not implemented)
    return redirect(url_for('dashboard.dashboard'))

@sso_auth.route('/providers')
def list_providers():
    """List available SSO providers for account"""
    account_id = request.args.get('account_id')
    
    # Get enabled providers
    providers = db.session.query(SSOConfig.provider_type, SSOConfig.provider_name).filter_by(
        enabled=True, account_id=account_id
    ).distinct().all()
    
    return render_template('auth/sso_providers.html', providers=providers, account_id=account_id)

# SSO Auto-Linking Functions
def _calculate_similarity(str1, str2):
    """Calculate similarity between two strings (0-100)"""
    return int(SequenceMatcher(None, str1.lower(), str2.lower()).ratio() * 100)

def _find_matching_team_member(sso_email, sso_name, sso_username=None):
    """
    Find the best matching team member for an SSO user
    Returns: (team_member, confidence_score, match_reason)
    """
    best_match = None
    best_score = 0
    best_reason = ""
    
    # Get all unlinked team members
    unlinked_members = TeamMember.query.filter_by(user_id=None).all()
    
    if not unlinked_members:
        return None, 0, "No unlinked team members available"
    
    for tm in unlinked_members:
        score = 0
        reasons = []
        
        # 1. Email matching (highest priority)
        if tm.email and sso_email:
            if tm.email.lower() == sso_email.lower():
                score = 100
                reasons.append("exact email match")
            elif tm.email.lower().split('@')[0] == sso_email.lower().split('@')[0]:
                score = 90
                reasons.append("username part of email matches")
        
        # 2. Name pattern matching
        if sso_name and tm.name:
            name_similarity = _calculate_similarity(tm.name, sso_name)
            if name_similarity >= 80:
                score = max(score, 85)
                reasons.append(f"name similarity: {name_similarity}%")
            elif name_similarity >= 60:
                score = max(score, 70)
                reasons.append(f"partial name match: {name_similarity}%")
        
        # 3. Username pattern matching (e.g., "acme A member-2" vs "acmeamember_2")
        if sso_username and tm.name:
            # Clean both strings for comparison
            clean_sso = re.sub(r'[^a-zA-Z0-9]', '', sso_username.lower())
            clean_tm = re.sub(r'[^a-zA-Z0-9]', '', tm.name.lower())
            
            username_similarity = _calculate_similarity(clean_sso, clean_tm)
            if username_similarity >= 75:
                score = max(score, 80)
                reasons.append(f"username pattern match: {username_similarity}%")
            
            # Check for number-based patterns (member-X vs member_X)
            sso_numbers = re.findall(r'\d+', sso_username)
            tm_numbers = re.findall(r'\d+', tm.name)
            if sso_numbers and tm_numbers and sso_numbers == tm_numbers:
                score = max(score, 75)
                reasons.append("matching member number")
        
        # Update best match if this score is higher
        if score > best_score:
            best_match = tm
            best_score = score
            best_reason = "; ".join(reasons)
    
    return best_match, best_score, best_reason

def _auto_link_team_member(user, sso_email, sso_name, sso_username=None, min_confidence=70):
    """
    Automatically link a user to a team member if confidence is high enough
    Returns: (success, team_member, confidence, reason)
    """
    try:
        team_member, confidence, reason = _find_matching_team_member(sso_email, sso_name, sso_username)
        
        if not team_member:
            return False, None, 0, "No matching team member found"
        
        if confidence < min_confidence:
            current_app.logger.info(f"🔍 SSO Auto-Link: Low confidence match for {sso_email} -> {team_member.name} ({confidence}%, need {min_confidence}%)")
            return False, team_member, confidence, f"Confidence too low: {confidence}% (minimum: {min_confidence}%)"
        
        # Perform the linking
        team_member.user_id = user.id
        db.session.add(team_member)
        db.session.commit()
        
        current_app.logger.info(f"✅ SSO Auto-Link: Successfully linked {sso_email} -> {team_member.name} ({confidence}%: {reason})")
        return True, team_member, confidence, f"Auto-linked: {reason}"
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"❌ SSO Auto-Link Error: {str(e)}")
        return False, None, 0, f"Error during linking: {str(e)}"