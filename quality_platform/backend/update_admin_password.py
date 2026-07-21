import sys
import os

# Add project root to path
sys.path.append('..')

from database import get_db
from models import User
from auth import get_password_hash

def update_admin_password():
    db = next(get_db())
    try:
        # Check if admin user exists
        admin_user = db.query(User).filter(User.username == 'admin').first()
        if admin_user:
            print(f'Admin user found: {admin_user.username}, {admin_user.email}')
            # Update password with fresh hash
            admin_user.hashed_password = get_password_hash('admin123')
            db.commit()
            print('Password updated successfully for admin user')
            print('You can now login with: admin / admin123')
        else:
            print('Admin user not found, creating new admin user...')
            # Create new admin user
            admin_user = User(
                username='admin',
                email='admin@example.com',
                hashed_password=get_password_hash('admin123'),
                full_name='System Administrator',
                role='admin',
                is_active=True
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)
            print('Admin user created successfully')
            print('You can now login with: admin / admin123')
    except Exception as e:
        print(f'Error: {e}')
        db.rollback()
    finally:
        db.close()

if __name__ == '__main__':
    update_admin_password()