import sys
sys.path.append('..')

from database import get_db
from models import User
from auth import verify_password, get_password_hash

# Test password verification
db = next(get_db())
try:
    admin_user = db.query(User).filter(User.username == 'admin').first()
    if admin_user:
        print(f'Admin user found: {admin_user.username}')
        print(f'Hashed password: {admin_user.hashed_password[:50]}...')
        
        # Test password verification
        test_password = 'admin123'
        is_valid = verify_password(test_password, admin_user.hashed_password)
        print(f'Password verification result: {is_valid}')
        
        # Test creating new hash
        new_hash = get_password_hash(test_password)
        print(f'New hash: {new_hash[:50]}...')
        
        # Test new hash verification
        is_valid_new = verify_password(test_password, new_hash)
        print(f'New hash verification: {is_valid_new}')
    else:
        print('Admin user not found')
finally:
    db.close()