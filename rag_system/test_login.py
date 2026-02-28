"""Test login endpoint directly"""
import sys
from app.services.user_service import get_user_by_username
from app.auth_utils import verify_password, create_access_token
from datetime import timedelta

try:
    # Test user lookup
    print("1. Looking up admin user...")
    user = get_user_by_username("admin")
    if not user:
        print("❌ User not found!")
        sys.exit(1)
    print(f"✓ User found: {user.username}")
    
    # Test password verification
    print("\n2. Verifying password...")
    if not verify_password("admin123", user.hashed_password):
        print("❌ Password verification failed!")
        sys.exit(1)
    print("✓ Password verified")
    
    # Test token creation
    print("\n3. Creating access token...")
    token_data = {
        "sub": user.username,
        "role": user.role.value
    }
    access_token = create_access_token(
        data=token_data,
        expires_delta=timedelta(minutes=1440)
    )
    print(f"✓ Token created: {access_token[:50]}...")
    
    print("\n✅ All tests passed! Login should work.")
    
except Exception as e:
    print(f"\n❌ Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
