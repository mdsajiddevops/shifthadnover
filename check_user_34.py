#!/usr/bin/env python3
"""
Check User ID 34
"""

import sys
sys.path.append('/app')

from app import app, db
from models.models import User

with app.app_context():
    user = User.query.get(34)
    if user:
        print(f'👤 User ID 34: {user.username} ({user.email})')
    else:
        print('❌ User ID 34 not found')