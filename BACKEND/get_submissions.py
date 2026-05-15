import requests
import os
from dotenv import load_dotenv
import json

load_dotenv()

token = os.getenv("KOBO_TOKEN")

# Directement l'URL de data depuis assets
url = "https://kf.kobotoolbox.org/api/v2/assets/aSSVtGFgeJti6Ln8KM5EzY/data/"
headers = {"Authorization": f"Token {token}"}

print(f"Testing: {url}")
print(f"Token: {token[:10]}...\n")

try:
    r = requests.get(url, headers=headers, timeout=10)
    print(f"Status: {r.status_code}")
    
    if r.status_code == 200:
        data = r.json()
        print(f"✅ Success!")
        print(f"Response keys: {list(data.keys())}")
        
        # Check if there are results
        if 'results' in data:
            submissions = data['results']
            print(f"Found {len(submissions)} submissions")
            
            if submissions:
                print(f"\nFirst submission:")
                print(json.dumps(submissions[0], indent=2))
        else:
            print(f"Full response:")
            print(json.dumps(data, indent=2)[:1000])
    else:
        print(f"❌ Error: {r.status_code}")
        print(f"Response: {r.text[:200]}")
        
except Exception as e:
    print(f"❌ Error: {e}")