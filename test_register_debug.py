import httpx
import json

base = "http://localhost:8000/api/v1"
email = "test_register_debug@example.com"
password = "TestPassword123!"

try:
    with httpx.Client(timeout=15) as client:
        print("=" * 60)
        print("TESTING REGISTRATION")
        print("=" * 60)
        r = client.post(
            f"{base}/auth/register",
            json={"email": email, "password": password}
        )
        print(f"Status: {r.status_code}")
        print(f"Headers: {dict(r.headers)}")
        print(f"\nFull Response:\n{r.text}")
        
        if r.status_code >= 400:
            try:
                print(f"\nParsed JSON:\n{json.dumps(r.json(), indent=2)}")
            except:
                pass
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
