from kobo_service import kobo_service
import json

forms = kobo_service.get_forms()
print(f"Number of forms: {len(forms)}")
print(f"\nFirst form structure:")
if forms:
    print(json.dumps(forms[0], indent=2))
else:
    print("No forms found")