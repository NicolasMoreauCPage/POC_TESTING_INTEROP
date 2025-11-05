"""
Test HTTP direct de la route /endpoints/1
"""
import requests

try:
    response = requests.get("http://127.0.0.1:8000/endpoints/1")
    print(f"Status: {response.status_code}")
    print(f"Headers: {response.headers.get('content-type')}")
    if response.status_code != 200:
        print(f"Error: {response.text[:500]}")
    else:
        print("✓ Page loaded successfully")
        print(f"Content length: {len(response.text)}")
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
