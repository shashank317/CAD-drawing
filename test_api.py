"""Quick script to test the /api/generate-cad endpoint and print the error body."""
from urllib.request import urlopen, Request
from urllib.error import HTTPError
import json

payload = json.dumps({
    "roller_diameter": 160.5,
    "bearing_width": 20.0,
    "shaft_diameter": 26.0,
    "overall_height": 50.0,
    "base_width": 100.5,
}).encode()

req = Request(
    "http://127.0.0.1:8000/api/generate-cad",
    data=payload,
    headers={"Content-Type": "application/json"},
    method="POST",
)

try:
    resp = urlopen(req)
    print("SUCCESS", resp.status)
except HTTPError as e:
    print(f"HTTP {e.code}")
    print(e.read().decode())
