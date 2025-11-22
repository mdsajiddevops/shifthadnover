#!/usr/bin/env python3
"""
Create TeamMembers for Users without them
"""

import sys
sys.path.append('/app')

from app import app, db
from models.models import User, TeamMember
from user_linking_service import UserTeamMemberLinkingService

with app.app_context():
    # Find users without TeamMember links
    unlinked_users = User.query.outerjoin(
        TeamMember, User.id == TeamMember.user_id
    ).filter(TeamMember.user_id.is_(None)).all()
    
    print(f'🔍 Found {len(unlinked_users)} users without TeamMember links')
    
    created_count = 0
    for user in unlinked_users:
        success, tm, message = UserTeamMemberLinkingService.create_teammember_for_user(user.id)
        if success:
            created_count += 1
            print(f'✅ {user.username} → Created TeamMember in {tm.team.name if hasattr(tm, "team") and tm.team else "team"}')
        else:
            print(f'❌ {user.username} → Failed: {message}')
    
    print(f'📊 Created {created_count} TeamMembers')