# 🚀 Shift Handover Application v2 - Complete HTTPS Ready

A comprehensive Flask-based shift handover management system with email notifications, HTTPS deployment, SSO integration, and modern admin interface.

## 🆕 Latest Updates (October 2025)

### ✨ Major Features Added

#### 📧 Email Recipients Management
- **Admin Dashboard Integration**: New "Email Recipients" tab in Secrets Management
- **Configurable Recipients**: Separate lists for handover notifications and priority alerts
- **Email Testing**: Built-in test functionality to verify email delivery
- **Toggle Notifications**: Enable/disable email notifications globally

#### 🔒 Production HTTPS Deployment
- **Complete SSL Setup**: Automated Let's Encrypt certificate generation
- **Nginx Reverse Proxy**: Production-grade proxy with security headers
- **Docker Compose**: Ready-to-deploy HTTPS configuration
- **Certificate Auto-Renewal**: Automated SSL certificate renewal setup

#### 🛡️ Enhanced Security
- **Security Headers**: HSTS, CSP, XSS protection
- **Rate Limiting**: Protection against brute force attacks
- **HTTPS Enforcement**: Automatic HTTP to HTTPS redirect
- **Secure Session Management**: Production-ready session configuration

## ✨ Key Features

### 🔐 SSO Authentication
- **Multi-Provider Support**: Google OAuth, Azure AD, SAML 2.0, Generic OAuth, LDAP
- **Admin Configuration**: Visual dashboard for managing SSO providers
- **Secure Storage**: Encrypted configuration storage using Fernet encryption
- **Role-Based Access**: Admin-only access to SSO configuration
- **Seamless Integration**: Built-in authentication flows with user provisioning

### 📊 Core Application Features
- **Shift Handover Management**: Create, edit, and track shift handovers
- **ServiceNow Integration**: Automated CTask assignment and incident tracking
- **Team Management**: Roster management with role-based permissions
- **Dashboard Analytics**: Real-time metrics and shift status monitoring
- **Audit Logging**: Comprehensive activity tracking and reporting
- **Email Notifications**: Automated notifications with configurable recipients

### 🎯 Quick Start for HTTPS Deployment

1. **Configure Domain**: Point your domain to server IP with NAT
2. **Environment Setup**: Copy `.env.https.template` to `.env.production`
3. **Deploy**: Run `deploy-https.ps1` or follow `QUICK_HTTPS_SETUP.md`

```powershell
# Quick deployment command
Copy-Item .env.https.template .env.production
# Edit .env.production with your domain and credentials
docker-compose -f docker-compose.https.yml up -d
```

### 🚀 Deployment Options

#### Development
```bash
docker-compose up -d
# Access: http://localhost:5000
```

#### Production HTTPS
```bash
docker-compose -f docker-compose.https.yml up -d
# Access: https://yourdomain.com
```

### 📚 Documentation

- **[Quick HTTPS Setup](QUICK_HTTPS_SETUP.md)**: Fast deployment guide
- **[Complete Deployment Guide](HTTPS_DEPLOYMENT_GUIDE.md)**: Detailed instructions
- **[Security Configuration](SECURE_CONFIGURATION_GUIDE.md)**: Security best practices
- **Export Features**: Export incidents/key points to PDF/CSV

### 🛠 Technical Stack
- **Backend**: Flask, SQLAlchemy, PostgreSQL/SQLite
- **Frontend**: Modern HTML5, CSS3, JavaScript with responsive design
- **Authentication**: Flask-Login with SSO integration
- **Security**: Encrypted configurations, CSRF protection, secure sessions
- **API Integration**: ServiceNow REST API, OAuth 2.0 providers

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Virtual environment
- Database (SQLite for development, PostgreSQL for production)

### Local Development Setup
```bash
# Clone from GitLab
git clone https://git.garage.epam.com/shift-handover-automation/shifthandover.git
cd shifthandover

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
copy .env.example .env
# Edit .env with your configuration

# Initialize database
python init_database.py

# Run the application
python app.py
```

### Access the Application
- **Main Application**: http://127.0.0.1:5000
- **SSO Configuration**: http://127.0.0.1:5000/admin/sso/ (Admin only)
- **Admin Dashboard**: http://127.0.0.1:5000/admin/configuration

## 🔧 SSO Configuration

### Google OAuth Setup
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create or select a project
3. Enable Google+ API
4. Create OAuth 2.0 credentials
5. Set authorized redirect URI: `http://your-domain/auth/sso/callback/google_oauth`
6. Copy Client ID and Client Secret to SSO configuration

### Azure AD Setup
1. Go to [Azure Portal](https://portal.azure.com/)
2. Navigate to Azure Active Directory > App registrations
3. Create new registration
4. Configure redirect URI: `http://your-domain/auth/sso/callback/azure_ad`
5. Generate client secret
6. Copy Application (client) ID and client secret

## 🚢 Docker Deployment

### Quick Start with Docker
```bash
# Build and start the containers
docker-compose up --build

# Access the application at http://localhost:5000

# Initialize the database (in a new terminal)
docker-compose exec web flask shell
>>> from app import db
>>> db.create_all()
>>> exit()
```

### Production Docker Setup
```bash
# Use production configuration
docker-compose -f docker-compose.prod.yml up --build
```

## 🔒 Security Features
- **Encrypted Storage**: All SSO configurations encrypted using Fernet
- **Environment Variables**: Sensitive data stored in environment variables
- **CSRF Protection**: Built-in cross-site request forgery protection
- **Session Security**: Secure session management with proper timeouts
- **Role-Based Access**: Admin-only access to sensitive configurations

## 🌐 GitLab Integration
- **Repository**: https://git.garage.epam.com/shift-handover-automation/shifthandover
- **CI/CD Pipelines**: Available for automated build and deployment
- **Merge Requests**: Code review and collaboration features
- **Project Management**: Issue tracking and milestone management

## 📊 Monitoring & Logging
- **Application Logs**: Comprehensive logging with rotating file handlers
- **Audit Trail**: User activity tracking and security auditing
- **Health Checks**: Built-in health monitoring endpoints
- **Performance Metrics**: Response time and usage analytics

---

**Repository**: https://git.garage.epam.com/shift-handover-automation/shifthandover
**Last Updated**: October 25, 2024
**Version**: 2.0 with SSO Integration and Modern UI

## Notes
- For proof-of-concept, authentication uses static credentials.
- Replace SMTP and DB credentials in `.env` for production use.

