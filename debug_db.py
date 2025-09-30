from src.database.database import SessionLocal, engine
from src.database.models import Base, User, Category
from src.api.simple_auth import get_password_hash
import traceback

print("🔍 Testing Database Setup...\n")

try:
    # Test 1: Database connection
    print("1. Testing database connection...")
    db = SessionLocal()
    print("✅ Database connection successful!")
    
    # Test 2: Check tables
    print("\n2. Checking tables...")
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"✅ Found tables: {tables}")
    
    # Test 3: Try to create tables
    print("\n3. Creating tables (if not exist)...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tables created/verified!")
    
    # Test 4: Test password hashing
    print("\n4. Testing password hashing...")
    test_password = "test123"
    hashed = get_password_hash(test_password)
    print(f"✅ Password hashed successfully: {hashed[:20]}...")
    
    # Test 5: Try to create a test user
    print("\n5. Testing user creation...")
    test_user = User(
        email="debugtest@example.com",
        username="debugtest",
        hashed_password=hashed
    )
    db.add(test_user)
    db.commit()
    print("✅ Test user created successfully!")
    
    # Clean up
    db.query(User).filter(User.username == "debugtest").delete()
    db.commit()
    print("✅ Test user cleaned up!")
    
    # Test 6: Check if categories exist
    print("\n6. Checking categories...")
    categories = db.query(Category).count()
    print(f"✅ Found {categories} categories")
    
    db.close()
    print("\n✅ All database tests passed!")
    
except Exception as e:
    print(f"\n❌ Error occurred: {type(e).__name__}")
    print(f"Error message: {str(e)}")
    print("\nFull traceback:")
    traceback.print_exc()
