from kobo_service import kobo_service
import json

forms = kobo_service.get_forms()
if forms:
    form_id = forms[0]["id"]
    title = forms[0].get("title", "N/A")

    print(f"Form ID: {form_id}")
    print(f"Form title: {title}")

    submissions = kobo_service.get_form_submissions(form_id)
    print(f"\n✅ Found {len(submissions)} submissions")

    if submissions:
        print(f"\nFirst submission fields:")
        print(json.dumps(submissions[0], indent=2))
else:
    print("❌ No forms found")