#!/bin/bash
# Helper script to activate the Python environment
echo "Activating Python virtual environment..."
source venv/bin/activate
echo "✅ Environment activated. Python path: $(which python)"
echo "✅ Pip path: $(which pip)"
echo "Ready to run Python scripts!"
