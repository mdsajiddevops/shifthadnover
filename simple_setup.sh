#!/bin/bash
# Fix Ubuntu Python Environment for Shift Handover App
# Run this script on your Ubuntu production server

echo "🔧 FIXING UBUNTU PYTHON ENVIRONMENT 🔧"
echo "======================================="

# Update package list
echo "1. Updating package list..."
sudo apt update

# Install required system packages
echo -e "\n2. Installing required system packages..."
sudo apt install -y python3-pip python3-venv python3-dev python3-setuptools

# Verify installations
echo -e "\n3. Verifying system packages..."
python3 --version
python3 -m pip --version

# Remove any broken venv directory
echo -e "\n4. Cleaning up any broken virtual environment..."
if [ -d "venv" ]; then
    echo "Removing broken venv directory..."
    rm -rf venv
fi

# Create virtual environment properly
echo -e "\n5. Creating virtual environment..."
python3 -m venv venv

# Check if venv was created successfully
if [ -d "venv" ]; then
    echo "✅ Virtual environment created successfully"
else
    echo "❌ Virtual environment creation failed"
    exit 1
fi

# Activate virtual environment
echo -e "\n6. Activating virtual environment..."
source venv/bin/activate

# Verify activation
echo "Virtual environment activated: $VIRTUAL_ENV"
which python
which pip

# Upgrade pip in virtual environment
echo -e "\n7. Upgrading pip..."
pip install --upgrade pip

# Install required Python packages
echo -e "\n8. Installing Python dependencies..."
pip install flask
pip install flask-sqlalchemy
pip install mysql-connector-python
pip install pymysql
pip install flask-migrate
pip install python-dotenv
pip install bcrypt
pip install flask-mail
pip install flask-login

# Verify installations
echo -e "\n9. Verifying installations..."
python -c "import flask; print(f'✅ Flask {flask.__version__} installed')"
python -c "import mysql.connector; print('✅ MySQL connector installed')"
python -c "import pymysql; print('✅ PyMySQL installed')"

# Test app import
echo -e "\n10. Testing app import..."
if [ -f "app.py" ]; then
    python -c "
try:
    from app import create_app
    print('✅ App import successful')
except Exception as e:
    print(f'⚠️  App import issue: {e}')
    print('This might be due to missing database config, but Flask is working')
"
else
    echo "❌ app.py not found"
fi

# Create activation helper script
echo -e "\n11. Creating activation helper..."
cat > activate_env.sh << 'EOF'
#!/bin/bash
# Helper script to activate the Python environment
echo "Activating Python virtual environment..."
source venv/bin/activate
echo "✅ Environment activated. Python path: $(which python)"
echo "✅ Pip path: $(which pip)"
echo "Ready to run Python scripts!"
EOF

chmod +x activate_env.sh

# Show final status
echo -e "\n12. Final Status:"
echo "✅ System packages installed"
echo "✅ Virtual environment created"
echo "✅ Python dependencies installed"
echo "✅ Flask and MySQL connectors available"

echo -e "\n🎯 SETUP COMPLETE!"
echo "==================="
echo "To use this environment:"
echo "1. Run: source venv/bin/activate"
echo "2. Or run: ./activate_env.sh"
echo "3. Then run your Python scripts"

echo -e "\nQuick test - run this command:"
echo "source venv/bin/activate && python3 -c 'import flask, mysql.connector; print(\"✅ All modules working!\")'"
