#!/usr/bin/env python3
import sys
import subprocess

# Check if API container is running
result = subprocess.run(['docker', 'ps', '--format', '{{.Names}} {{.Status}}'], capture_output=True, text=True)
print("=== Docker Containers ===")
print(result.stdout)
if result.stderr:
    print("STDERR:", result.stderr)

print("\n=== API Logs ===")
result = subprocess.run(['docker', 'logs', 'rozgaar-api', '--tail', '50'], capture_output=True, text=True)
print(result.stdout)
if result.stderr:
    print("STDERR:", result.stderr)

print("\n=== Testing API ===")
try:
    import httpx
    r = httpx.get('http://localhost:8000/api/v1/docs', timeout=2)
    print(f"API Status: {r.status_code}")
except Exception as e:
    print(f"API Error: {e}")
