import requests
from dotenv import load_dotenv
import os

load_dotenv()

token = os.getenv("KOBO_TOKEN")
username = os.getenv("KOBO_USERNAME")

print(f"Token: {token}")
print(f"Username: {username}\n")

# Essayer différentes URLs
urls_to_test = [
    "https://kf.kobotoolbox.org/api/v2/forms/",
    "https://kf.kobotoolbox.org/api/v1/forms/",
    "https://kf.kobotoolbox.org/api/forms/",
    "https://kf.kobotoolbox.org/api/v2/assets/",
    "https://kf.kobotoolbox.org/api/v2/users/",
]

for url in urls_to_test:
    print(f"Testing: {url}")
    headers = {"Authorization": f"Token {token}"}
    try:
        r = requests.get(url, headers=headers, timeout=5)
        print(f"  Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list):
                print(f"  ✅ SUCCESS! Found {len(data)} items")
            elif isinstance(data, dict) and 'results' in data:
                print(f"  ✅ SUCCESS! Found {len(data['results'])} items")
            else:
                print(f"  ✅ SUCCESS! Response: {str(data)[:100]}")
            break
        else:
            print(f"  ❌ Failed")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    print()