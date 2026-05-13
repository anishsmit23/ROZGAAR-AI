#!/usr/bin/env python3
import subprocess
import time

# Wait a bit for containers
time.sleep(5)

# Check container status
print("=" * 60)
print("CONTAINER STATUS")
print("=" * 60)
result = subprocess.run(["docker", "compose", "ps", "-a"], capture_output=True, text=True)
print(result.stdout)

# Check UI logs
print("\n" + "=" * 60)
print("UI CONTAINER LOGS (last 20 lines)")
print("=" * 60)
result = subprocess.run(["docker", "compose", "logs", "ui", "--tail=20"], capture_output=True, text=True)
print(result.stdout)
if result.stderr:
    print("STDERR:", result.stderr)

# Check if Streamlit is listening
print("\n" + "=" * 60)
print("CHECKING PORTS")
print("=" * 60)
import socket
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2)
    result = s.connect_ex(('localhost', 8501))
    if result == 0:
        print("✓ Port 8501 (Streamlit) is OPEN")
    else:
        print("✗ Port 8501 (Streamlit) is CLOSED")
    s.close()
except Exception as e:
    print(f"✗ Error checking port: {e}")

try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2)
    result = s.connect_ex(('localhost', 8000))
    if result == 0:
        print("✓ Port 8000 (API) is OPEN")
    else:
        print("✗ Port 8000 (API) is CLOSED")
    s.close()
except Exception as e:
    print(f"✗ Error checking port: {e}")
