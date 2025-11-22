# Quick Setup Script for Google SSO
# Run this script to set up Google OAuth SSO integration

Write-Host "🔐 Setting up Google SSO Integration..." -ForegroundColor Green

# Step 1: Install required Python packages
Write-Host "`n📦 Installing required packages..." -ForegroundColor Yellow
& .venv\Scripts\python.exe -m pip install cryptography requests

# Step 2: Generate encryption key for SSO config
Write-Host "`n🔑 Generating SSO encryption key..." -ForegroundColor Yellow
$encryptionKey = & .venv\Scripts\python.exe -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
Write-Host "Generated encryption key: $encryptionKey" -ForegroundColor Cyan

# Step 3: Set environment variable (for current session)
$env:SSO_ENCRYPTION_KEY = $encryptionKey
Write-Host "✅ Set SSO_ENCRYPTION_KEY environment variable" -ForegroundColor Green

# Step 4: Create migration for SSO config table
Write-Host "`n🗄️ Creating database migration for SSO..." -ForegroundColor Yellow
& .venv\Scripts\python.exe -c @"
from app import app, db
from models.sso_config import SSOConfig

with app.app_context():
    try:
        # Create SSO config table
        db.create_all()
        print('✅ SSO configuration table created successfully')
    except Exception as e:
        print(f'⚠️  Database setup: {e}')
"@

# Step 5: Register SSO blueprints
Write-Host "`n🔧 Checking Flask app configuration..." -ForegroundColor Yellow
& .venv\Scripts\python.exe -c @"
import sys
import os

# Check if SSO routes are imported in app.py
app_py_path = 'app.py'
if os.path.exists(app_py_path):
    with open(app_py_path, 'r') as f:
        content = f.read()
        
    if 'sso_auth' not in content:
        print('⚠️  Need to add SSO blueprints to app.py')
        print('Add these lines to your app.py:')
        print('')
        print('from routes.sso_auth import sso_auth')
        print('from routes.sso_config import sso_config_bp')
        print('')
        print('app.register_blueprint(sso_auth)')
        print('app.register_blueprint(sso_config_bp)')
    else:
        print('✅ SSO blueprints already configured')
else:
    print('⚠️  app.py not found in current directory')
"@

Write-Host "`n✅ Google SSO setup complete!" -ForegroundColor Green
Write-Host "`n📋 Next steps:" -ForegroundColor Cyan
Write-Host "1. Go to Google Cloud Console (https://console.cloud.google.com/)" -ForegroundColor White
Write-Host "2. Create OAuth 2.0 credentials" -ForegroundColor White
Write-Host "3. Set redirect URI: http://localhost:5000/auth/sso/callback/oauth" -ForegroundColor White
Write-Host "4. Start your Flask app: python app.py" -ForegroundColor White
Write-Host "5. Navigate to /admin/sso/ to configure Google OAuth" -ForegroundColor White
Write-Host "6. Use the Google OAuth configuration template" -ForegroundColor White

Write-Host "`n🔑 IMPORTANT: Save this encryption key to your .env file:" -ForegroundColor Red
Write-Host "SSO_ENCRYPTION_KEY=$encryptionKey" -ForegroundColor Yellow

Write-Host "`n🚀 Ready to configure Google SSO!" -ForegroundColor Green