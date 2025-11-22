from app import app, db
from models.models import User
from werkzeug.security import generate_password_hash

# Initialize Flask app context
with app.app_context():
    # Check if superadmin already exists
    existing_admin = User.query.filter_by(username='admin').first()
    if existing_admin:
        print("✅ Superadmin already exists")
    else:
        # Create superadmin user
        admin_user = User(
            username='admin',
            email='admin@company.com',
            password=generate_password_hash('admin123'),
            role='super_admin',
            first_name='System',
            last_name='Administrator'
        )
        
        db.session.add(admin_user)
        db.session.commit()
        print("✅ Superadmin created successfully")
        print("   Username: admin")
        print("   Password: admin123")
        print("   Role: super_admin")