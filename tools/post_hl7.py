import httpx
from pathlib import Path
p = Path(__file__).parent.parent / 'test' / 'sample_hl7.txt'
payload = p.read_text()
url = 'http://127.0.0.1:8001/messages/send'
print('Posting to', url)
resp = httpx.post(url, data={'payload': payload, 'kind': 'MLLP'})
print('status', resp.status_code)
print(resp.text[:500])
