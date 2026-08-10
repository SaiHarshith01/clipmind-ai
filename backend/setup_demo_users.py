from core.database import SessionLocal
from models.schema import User, UserRole
from core.security import get_password_hash

# Connect to the database
db = SessionLocal()

print("Creating presentation users...")

# 1. Create an Admin User (Allowed to upload)
admin_email = "admin@clipmind.com"
if not db.query(User).filter(User.email == admin_email).first():
    admin = User(
        email=admin_email,
        hashed_password=get_password_hash("admin123"),
        role=UserRole.ADMIN
    )
    db.add(admin)

# 2. Create a Learner User (Blocked from uploading)
learner_email = "learner@clipmind.com"
if not db.query(User).filter(User.email == learner_email).first():
    learner = User(
        email=learner_email,
        hashed_password=get_password_hash("learner123"),
        role=UserRole.LEARNER
    )
    db.add(learner)

db.commit()
db.close()

print("✅ Demo users created successfully!")