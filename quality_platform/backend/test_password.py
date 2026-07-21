from auth import verify_password
from database import engine
from sqlalchemy import text

def test_password():
    with engine.connect() as conn:
        result = conn.execute(text('SELECT hashed_password FROM users WHERE username = "admin"')).fetchone()
        if result:
            hashed_password = result[0]
            print('Hashed password from DB:', hashed_password)
            
            # Test password verification
            test_password = "admin123"
            is_valid = verify_password(test_password, hashed_password)
            print(f'Password "{test_password}" is valid:', is_valid)
            
            # Try another common password
            test_password2 = "admin"
            is_valid2 = verify_password(test_password2, hashed_password)
            print(f'Password "{test_password2}" is valid:', is_valid2)
        else:
            print('Admin user not found')

if __name__ == "__main__":
    test_password()