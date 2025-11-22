"""
SSO Configuration UI Routes
Provides admin interface for managing SSO providers
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models.models import db, Account
from models.sso_config import SSOConfig
# Simple role requirement function instead of importing utils
import json

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models.models import db, Account
from models.sso_config import SSOConfig
import json

# Simple role check function
def check_admin_role():
    """Check if current user is admin"""
    if not current_user.is_authenticated:
        return False
    return current_user.role in ['super_admin', 'account_admin']

sso_config_bp = Blueprint('sso_config', __name__, url_prefix='/admin/sso')

@sso_config_bp.route('/')
@login_required
def sso_dashboard():
    """SSO configuration dashboard"""
    if not check_admin_role():
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard.dashboard'))
        
    # Get account context
    account_id = None
    if current_user.role == 'account_admin':
        account_id = current_user.account_id
    
    # Get configured providers
    providers = get_configured_providers(account_id)
    
    return render_template('admin/sso_dashboard.html', providers=providers, account_id=account_id)

@sso_config_bp.route('/configure/<provider_type>')
@login_required
def configure_provider(provider_type):
    """Configure SSO provider"""
    if not check_admin_role():
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard.dashboard'))
        
    account_id = None
    if current_user.role == 'account_admin':
        account_id = current_user.account_id
    
    # Get existing configuration
    config = SSOConfig.get_provider_config(provider_type, account_id)
    
    # Get provider template
    template_config = get_provider_template(provider_type)
    
    return render_template(
        'admin/sso_configure.html',
        provider_type=provider_type,
        config=config,
        template=template_config,
        account_id=account_id
    )

@sso_config_bp.route('/save/<provider_type>', methods=['POST'])
@login_required
def save_provider_config(provider_type):
    """Save SSO provider configuration"""
    if not check_admin_role():
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard.dashboard'))
        
    try:
        account_id = None
        if current_user.role == 'account_admin':
            account_id = current_user.account_id
        
        # Get form data
        provider_name = request.form.get('provider_name')
        enabled = request.form.get('enabled') == 'on'
        
        # Build configuration dictionary
        config_dict = {}
        template = get_provider_template(provider_type)
        
        for field in template['fields']:
            field_name = field['name']
            field_value = request.form.get(field_name)
            if field_value:
                config_dict[field_name] = field_value
        
        # Special handling for enabled state
        config_dict['enabled'] = 'true' if enabled else 'false'
        
        # Save configuration
        SSOConfig.set_provider_config(
            provider_type=provider_type,
            provider_name=provider_name,
            config_dict=config_dict,
            account_id=account_id,
            encrypt_keys=['client_secret', 'private_key', 'password', 'certificate_key']
        )
        
        flash(f'SSO provider {provider_name} configured successfully', 'success')
        return redirect(url_for('sso_config.sso_dashboard'))
        
    except Exception as e:
        flash(f'Error configuring SSO provider: {str(e)}', 'error')
        return redirect(url_for('sso_config.configure_provider', provider_type=provider_type))

@sso_config_bp.route('/test/<provider_type>')
@login_required
def test_provider(provider_type):
    """Test SSO provider configuration"""
    if not check_admin_role():
        return jsonify({'success': False, 'error': 'Access denied'})
        
    try:
        account_id = None
        if current_user.role == 'account_admin':
            account_id = current_user.account_id
        
        # Get configuration
        config = SSOConfig.get_provider_config(provider_type, account_id)
        
        if not config:
            return jsonify({'success': False, 'error': 'Provider not configured'})
        
        # Perform basic connectivity test
        test_result = perform_provider_test(provider_type, config)
        
        return jsonify(test_result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@sso_config_bp.route('/delete/<provider_type>', methods=['POST'])
@login_required
def delete_provider(provider_type):
    """Delete SSO provider configuration"""
    if not check_admin_role():
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard.dashboard'))
        
    try:
        account_id = None
        if current_user.role == 'account_admin':
            account_id = current_user.account_id
        
        # Delete configuration
        SSOConfig.query.filter_by(provider_type=provider_type, account_id=account_id).delete()
        db.session.commit()
        
        flash(f'SSO provider {provider_type} deleted successfully', 'success')
        
    except Exception as e:
        flash(f'Error deleting SSO provider: {str(e)}', 'error')
    
    return redirect(url_for('sso_config.sso_dashboard'))

def get_configured_providers(account_id=None):
    """Get list of configured SSO providers"""
    query = db.session.query(
        SSOConfig.provider_type,
        SSOConfig.provider_name,
        SSOConfig.enabled
    ).filter_by(account_id=account_id).distinct()
    
    providers = {}
    for provider_type, provider_name, enabled in query:
        if provider_type not in providers:
            providers[provider_type] = {
                'name': provider_name,
                'enabled': False,
                'type': provider_type
            }
        if enabled:
            providers[provider_type]['enabled'] = True
    
    return providers

def get_provider_template(provider_type):
    """Get configuration template for SSO provider"""
    templates = {
        'saml': {
            'name': 'SAML 2.0',
            'description': 'Enterprise SAML 2.0 Single Sign-On',
            'fields': [
                {'name': 'entity_id', 'label': 'Entity ID', 'type': 'text', 'required': True},
                {'name': 'sso_url', 'label': 'SSO URL', 'type': 'url', 'required': True},
                {'name': 'slo_url', 'label': 'Single Logout URL', 'type': 'url', 'required': False},
                {'name': 'acs_url', 'label': 'Assertion Consumer Service URL', 'type': 'url', 'required': True},
                {'name': 'certificate', 'label': 'X.509 Certificate', 'type': 'textarea', 'required': True},
                {'name': 'private_key', 'label': 'Private Key', 'type': 'textarea', 'required': False, 'sensitive': True},
                {'name': 'name_id_format', 'label': 'NameID Format', 'type': 'select', 'options': [
                    'urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress',
                    'urn:oasis:names:tc:SAML:2.0:nameid-format:persistent',
                    'urn:oasis:names:tc:SAML:2.0:nameid-format:transient'
                ]},
                {'name': 'auto_provision', 'label': 'Auto-provision Users', 'type': 'checkbox'},
                {'name': 'default_role', 'label': 'Default Role', 'type': 'select', 'options': ['user', 'team_admin']}
            ]
        },
        'azure_ad': {
            'name': 'Azure Active Directory',
            'description': 'Microsoft Azure AD OpenID Connect',
            'fields': [
                {'name': 'tenant_id', 'label': 'Tenant ID', 'type': 'text', 'required': True},
                {'name': 'client_id', 'label': 'Application (Client) ID', 'type': 'text', 'required': True},
                {'name': 'client_secret', 'label': 'Client Secret', 'type': 'password', 'required': True, 'sensitive': True},
                {'name': 'redirect_uri', 'label': 'Redirect URI', 'type': 'url', 'required': True},
                {'name': 'auth_endpoint', 'label': 'Authorization Endpoint', 'type': 'url', 'required': True,
                 'default': 'https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize'},
                {'name': 'token_endpoint', 'label': 'Token Endpoint', 'type': 'url', 'required': True,
                 'default': 'https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token'},
                {'name': 'userinfo_endpoint', 'label': 'User Info Endpoint', 'type': 'url', 'required': True,
                 'default': 'https://graph.microsoft.com/v1.0/me'},
                {'name': 'auto_provision', 'label': 'Auto-provision Users', 'type': 'checkbox'},
                {'name': 'default_role', 'label': 'Default Role', 'type': 'select', 'options': ['user', 'team_admin']}
            ]
        },
        'google_oauth': {
            'name': 'Google OAuth 2.0',
            'description': 'Google Gmail / Workspace authentication',
            'fields': [
                {'name': 'client_id', 'label': 'Google Client ID', 'type': 'text', 'required': True,
                 'placeholder': 'your-app.googleusercontent.com'},
                {'name': 'client_secret', 'label': 'Google Client Secret', 'type': 'password', 'required': True, 'sensitive': True},
                {'name': 'authorization_endpoint', 'label': 'Authorization Endpoint', 'type': 'url', 'required': True,
                 'default': 'https://accounts.google.com/o/oauth2/v2/auth'},
                {'name': 'token_endpoint', 'label': 'Token Endpoint', 'type': 'url', 'required': True,
                 'default': 'https://oauth2.googleapis.com/token'},
                {'name': 'userinfo_endpoint', 'label': 'User Info Endpoint', 'type': 'url', 'required': True,
                 'default': 'https://www.googleapis.com/oauth2/v2/userinfo'},
                {'name': 'redirect_uri', 'label': 'Redirect URI', 'type': 'url', 'required': True,
                 'default': 'http://localhost:5000/auth/sso/callback/oauth'},
                {'name': 'scope', 'label': 'Scope', 'type': 'text', 'default': 'openid profile email'},
                {'name': 'auto_provision', 'label': 'Auto-provision Users', 'type': 'checkbox', 'default': True},
                {'name': 'default_role', 'label': 'Default Role', 'type': 'select', 'options': ['user', 'team_admin'], 'default': 'user'}
            ]
        },
        'oauth': {
            'name': 'Generic OAuth 2.0',
            'description': 'Generic OAuth 2.0 / OpenID Connect provider',
            'fields': [
                {'name': 'client_id', 'label': 'Client ID', 'type': 'text', 'required': True},
                {'name': 'client_secret', 'label': 'Client Secret', 'type': 'password', 'required': True, 'sensitive': True},
                {'name': 'authorization_endpoint', 'label': 'Authorization Endpoint', 'type': 'url', 'required': True},
                {'name': 'token_endpoint', 'label': 'Token Endpoint', 'type': 'url', 'required': True},
                {'name': 'userinfo_endpoint', 'label': 'User Info Endpoint', 'type': 'url', 'required': True},
                {'name': 'redirect_uri', 'label': 'Redirect URI', 'type': 'url', 'required': True},
                {'name': 'scope', 'label': 'Scope', 'type': 'text', 'default': 'openid profile email'},
                {'name': 'auto_provision', 'label': 'Auto-provision Users', 'type': 'checkbox'},
                {'name': 'default_role', 'label': 'Default Role', 'type': 'select', 'options': ['user', 'team_admin']}
            ]
        },
        'ldap': {
            'name': 'LDAP / Active Directory',
            'description': 'LDAP or Windows Active Directory authentication',
            'fields': [
                {'name': 'server_url', 'label': 'LDAP Server URL', 'type': 'text', 'required': True,
                 'placeholder': 'ldap://domain.com:389 or ldaps://domain.com:636'},
                {'name': 'bind_dn', 'label': 'Bind DN', 'type': 'text', 'required': True,
                 'placeholder': 'CN=service_account,OU=Users,DC=domain,DC=com'},
                {'name': 'bind_password', 'label': 'Bind Password', 'type': 'password', 'required': True, 'sensitive': True},
                {'name': 'base_dn', 'label': 'Base DN', 'type': 'text', 'required': True,
                 'placeholder': 'OU=Users,DC=domain,DC=com'},
                {'name': 'user_filter', 'label': 'User Filter', 'type': 'text', 'required': True,
                 'default': '(sAMAccountName={username})'},
                {'name': 'email_attribute', 'label': 'Email Attribute', 'type': 'text', 'default': 'mail'},
                {'name': 'first_name_attribute', 'label': 'First Name Attribute', 'type': 'text', 'default': 'givenName'},
                {'name': 'last_name_attribute', 'label': 'Last Name Attribute', 'type': 'text', 'default': 'sn'},
                {'name': 'auto_provision', 'label': 'Auto-provision Users', 'type': 'checkbox'},
                {'name': 'default_role', 'label': 'Default Role', 'type': 'select', 'options': ['user', 'team_admin']}
            ]
        }
    }
    
    return templates.get(provider_type, {})

def perform_provider_test(provider_type, config):
    """Perform basic connectivity test for SSO provider"""
    try:
        if provider_type == 'saml':
            # Test SAML metadata endpoint
            import requests
            metadata_url = config.get('metadata_url')
            if metadata_url:
                response = requests.get(metadata_url, timeout=10)
                if response.status_code == 200:
                    return {'success': True, 'message': 'SAML metadata accessible'}
                else:
                    return {'success': False, 'error': f'SAML metadata returned {response.status_code}'}
            else:
                return {'success': True, 'message': 'Configuration saved (metadata URL not provided for testing)'}
        
        elif provider_type in ['azure_ad', 'oauth']:
            # Test OAuth endpoints
            import requests
            auth_endpoint = config.get('auth_endpoint') or config.get('authorization_endpoint')
            if auth_endpoint:
                try:
                    response = requests.head(auth_endpoint, timeout=10)
                    if response.status_code in [200, 400, 405]:  # 400 is OK for OAuth endpoints (missing required params)
                        return {'success': True, 'message': 'OAuth endpoints accessible'}
                    else:
                        return {'success': False, 'error': f'OAuth endpoint "{auth_endpoint}" returned {response.status_code}'}
                except Exception as e:
                    return {'success': False, 'error': f'Failed to test OAuth endpoint "{auth_endpoint}": {str(e)}'}
            else:
                return {'success': True, 'message': 'Configuration saved (no endpoints to test)'}
        
        elif provider_type == 'ldap':
            # Test LDAP connection
            import ldap3
            server = ldap3.Server(config.get('server_url'))
            conn = ldap3.Connection(
                server,
                user=config.get('bind_dn'),
                password=config.get('bind_password'),
                auto_bind=True
            )
            if conn.bound:
                conn.unbind()
                return {'success': True, 'message': 'LDAP connection successful'}
            else:
                return {'success': False, 'error': 'LDAP connection failed'}
        
        else:
            return {'success': True, 'message': 'Configuration saved (no test available for this provider)'}
    
    except Exception as e:
        return {'success': False, 'error': f'Test failed: {str(e)}'}