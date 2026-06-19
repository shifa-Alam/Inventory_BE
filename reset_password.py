"""
Run this script to reset the admin password:
    python reset_password.py
"""
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.user import User

USERNAME = "admin"       # change if your username is different
NEW_PASSWORD = "Admin@1234"  # change to whatever you want (min 8 chars)

db = SessionLocal()

user = db.query(User).filter(User.username == USERNAME).first()

if not user:
    print(f"No user found with username '{USERNAME}'.")
    print("All users in the database:")
    for u in db.query(User).all():
        print(f"  id={u.id}  username={u.username}  role={u.role}")
else:
    user.password = hash_password(NEW_PASSWORD)
    db.commit()
    print(f"Password reset successfully for user '{USERNAME}'.")
    print(f"New password: {NEW_PASSWORD}")

db.close()
