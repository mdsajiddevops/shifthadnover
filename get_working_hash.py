from werkzeug.security import generate_password_hash
import sys
sys.path.append('/app')
from app import app
from models.models import User

def update_password():
    with app.app_context():
        # Generate hash
        new_hash = generate_password_hash('test123')
        print(f'Generated hash: {new_hash}')
        
        # Update user directly through SQLAlchemy
        user = User.query.filter_by(username='testuser').first()
        if user:
            user.password = new_hash
            user.email = 'testuser@epam.com'
            user.role = 'user'
            user.first_login = True
            user.onboarding_completed = False
            user.account_id = None
            user.team_id = None
            user.is_active = True
            user.status = 'active'
            
            from models.models import db
            db.session.commit()
            
            print(' User updated successfully via SQLAlchemy')
            print(f'Needs onboarding: {user.needs_onboarding}')
        else:
            print(' User not found')

if __name__ == '__main__':
    update_password()
