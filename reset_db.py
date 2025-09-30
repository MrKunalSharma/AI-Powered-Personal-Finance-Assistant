import os
from src.database.database import engine, SessionLocal
from src.database.models import Base, User

# Drop all tables
print("Dropping all tables...")
Base.metadata.drop_all(bind=engine)

# Recreate tables
print("Creating tables...")
Base.metadata.create_all(bind=engine)

# Verify
db = SessionLocal()
user_count = db.query(User).count()
print(f"User count after reset: {user_count}")
db.close()

print("Database reset complete!")
