import httpx
import json

try:
    response = httpx.get("http://localhost:8002/openapi.json")
    if response.status_code == 200:
        schema = response.json()
        paths = schema.get("paths", {}).keys()
        print("\n--- Available Routes on localhost:8002 ---")
        for p in paths:
            print(p)
        print("------------------------------------------\n")
        
        if "/route/optimize" in paths:
            print("SUCCESS: /route/optimize is present.")
        else:
            print("FAILURE: /route/optimize is MISSING.")
    else:
        print(f"Failed to fetch openapi.json. Status: {response.status_code}")
except Exception as e:
    print(f"Connection failed: {e}")

