from database import engine
from sqlalchemy import text

def check_admin_user():
    with engine.connect() as conn:
        result = conn.execute(text('SELECT * FROM users WHERE username = "admin"')).fetchall()
        print('Admin user:', result)

if __name__ == "__main__":
    check_admin_user()