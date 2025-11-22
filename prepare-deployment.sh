#!/bin/bash

# Local preparation script for GCP deployment
echo "🛠️ Preparing Shift Handover App for GCP deployment..."

# Check if required files exist
echo "✅ Checking deployment files..."
required_files=("Dockerfile.prod" "docker-compose.prod.yml" ".env.production" "deploy-gcp.sh" "GCP_DEPLOYMENT_GUIDE.md")

for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo "✓ $file exists"
    else
        echo "✗ $file missing"
        exit 1
    fi
done

# Create .env from template if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 Creating .env from template..."
    cp .env.production .env
    echo "⚠️  Please edit .env with your actual configuration values!"
fi

# Create .dockerignore if it doesn't exist
if [ ! -f ".dockerignore" ]; then
    echo "📝 Creating .dockerignore..."
    cat > .dockerignore << EOF
# Git
.git
.gitignore

# Python
__pycache__
*.pyc
*.pyo
*.pyd
.Python
env
pip-log.txt
pip-delete-this-directory.txt
.tox
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
*.log
.git
.mypy_cache
.pytest_cache
.hypothesis

# Virtual environments
.venv
venv/
ENV/

# Local development
.env.local
.env.development
instance/
.webassets-cache

# IDEs
.vscode
.idea
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Deployment files (keep local)
deploy-gcp.sh
GCP_DEPLOYMENT_GUIDE.md
prepare-deployment.sh
EOF
fi

echo ""
echo "🎉 Deployment files are ready!"
echo ""
echo "📋 Next steps:"
echo "1. Edit .env with your actual configuration"
echo "2. Commit and push your code to a Git repository"
echo "3. Follow the GCP_DEPLOYMENT_GUIDE.md for deployment instructions"
echo ""
echo "📖 Quick start:"
echo "   1. Create GCP VM instance"
echo "   2. SSH into the VM"
echo "   3. Clone your repository"
echo "   4. Run ./deploy-gcp.sh"
echo ""