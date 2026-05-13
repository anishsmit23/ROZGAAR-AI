import httpx
import json

base = "http://localhost:8000/api/v1"
email = "test_login_debug@example.com"
password = "TestPassword123!"

try:
    with httpx.Client(timeout=15) as client:
        # Register
        print("=" * 60)
        print("REGISTER REQUEST")
        print("=" * 60)
        r1 = client.post(
            f"{base}/auth/register",
            json={"email": email, "password": password}
        )
        print(f"Status: {r1.status_code}")
        print(f"Response: {r1.text[:500]}")
        
        # Login
        print("\n" + "=" * 60)
        print("LOGIN REQUEST")
        print("=" * 60)
        r2 = client.post(
            f"{base}/auth/jwt/login",
            data={"username": email, "password": password}
        )
        print(f"Status: {r2.status_code}")
        print(f"Response: {r2.text[:1000]}")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
