from src.database.database import engine, SessionLocal
from src.database.models import Base

# Drop and recreate all tables
print("Updating database schema...")
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)
print("✅ Database schema updated!")

# Verify new tables
from sqlalchemy import inspect
inspector = inspect(engine)
tables = inspector.get_table_names()
print(f"Tables in database: {tables}")

# Check if budgets and alerts tables exist
if 'budgets' in tables and 'alerts' in tables:
    print("✅ Budget and Alert tables created successfully!")
else:
    print("❌ Error: Budget tables not created")
