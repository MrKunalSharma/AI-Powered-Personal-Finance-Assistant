from src.api.auth import get_password_hash, verify_password

# Test password hashing
try:
    print("Testing password hashing...")
    password = "test123"
    hashed = get_password_hash(password)
    print(f"✅ Password hashed successfully: {hashed[:20]}...")
    
    # Test verification
    is_valid = verify_password(password, hashed)
    print(f"✅ Password verification: {is_valid}")
except Exception as e:
    print(f"❌ Error: {e}")
