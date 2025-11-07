"""Debug API response."""
import requests

# Use eg_ids parameter like the frontend does
eg_ids = "4,6,7,8,9,10,11,12,13"
url = f'http://127.0.0.1:8000/api/structure/tree?eg_ids={eg_ids}'

print(f"Requesting: {url}\n")
r = requests.get(url)

print(f"Status Code: {r.status_code}")
print(f"Content-Type: {r.headers.get('content-type')}")
print(f"\nResponse Text (first 1000 chars):")
print(r.text[:1000])

if r.status_code == 200:
    try:
        data = r.json()
        print(f"\n\nJSON parsed successfully!")
        print(f"Type: {type(data)}")
        if isinstance(data, list):
            print(f"Length: {len(data)}")
        elif isinstance(data, dict):
            print(f"Keys: {list(data.keys())}")
    except Exception as e:
        print(f"\n\nFailed to parse JSON: {e}")
