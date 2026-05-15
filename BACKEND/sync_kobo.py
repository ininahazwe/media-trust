#!/usr/bin/env python3
"""
Synchronize KoboToolkit responses to SQLite database
"""

import json
import requests
import os
from dotenv import load_dotenv
from database import SessionLocal
from models import Outlet, Respondent, Response, MTIIndex

load_dotenv()

# Mapping des champs Kobo vers scores (0-100)
RESPONSE_MAPPING = {
    "strongly_agree": 100,
    "agree": 75,
    "neither": 50,
    "disagree": 25,
    "strongly_disagree": 0,
}

def kobo_response_to_score(response_value):
    """Convertit une réponse Kobo en score 0-100"""
    if not response_value:
        return 50  # Valeur par défaut
    return RESPONSE_MAPPING.get(str(response_value).lower(), 50)

def sync_kobo_responses():
    """Fetch from Kobo and save to SQLite"""

    # Get form data directly
    token = os.getenv("KOBO_TOKEN")
    form_uid = "aSSVtGFgeJti6Ln8KM5EzY"  # From inspect_kobo output

    url = f"https://kf.kobotoolbox.org/api/v2/assets/{form_uid}/data/"
    headers = {"Authorization": f"Token {token}"}

    print(f"📋 Fetching data from: {url}")

    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching data: {e}")
        return

    submissions = data.get('results', [])
    print(f"📊 Found {len(submissions)} submissions")

    if not submissions:
        print("⚠️  No submissions to sync")
        return

    db = SessionLocal()
    synced = 0

    for sub in submissions:
        try:
            # Extract data
            outlet_name = sub.get('rating/outlet_name', 'Unknown')
            outlet_name = outlet_name.title() if outlet_name else 'Unknown'

            respondent_name = f"R{sub.get('_id', 'Unknown')}"
            respondent_role = "Survey Respondent"

            kobo_id = str(sub.get('_uuid', ''))

            # Extract MTI scores from Kobo responses
            accuracy = kobo_response_to_score(sub.get('rating/outlet_grp/outlet_accuracy'))
            verification = kobo_response_to_score(sub.get('rating/outlet_grp/outlet_verify'))
            independence = kobo_response_to_score(sub.get('rating/outlet_grp/outlet_indep'))
            fair_balanced = kobo_response_to_score(sub.get('rating/outlet_grp/outlet_fair'))
            public_interest = kobo_response_to_score(sub.get('rating/outlet_grp/outlet_public'))
            corrections = kobo_response_to_score(sub.get('rating/outlet_grp/outlet_correct'))

            print(f"\n📝 Processing: {outlet_name}")
            print(f"   Accuracy: {accuracy}, Verification: {verification}")

            # Create or get outlet
            outlet = db.query(Outlet).filter(
                Outlet.outlet_name == outlet_name
            ).first()

            if not outlet:
                outlet = Outlet(
                    outlet_name=outlet_name,
                    outlet_type="Radio",  # Default
                    region=sub.get('geo/region', 'Unknown')
                )
                db.add(outlet)
                db.flush()
                print(f"   ✅ Created outlet: {outlet_name}")
            else:
                print(f"   ℹ️  Outlet exists: {outlet_name}")

            # Create or get respondent
            respondent = db.query(Respondent).filter(
                Respondent.outlet_id == outlet.id,
                Respondent.respondent_name == respondent_name
            ).first()

            if not respondent:
                respondent = Respondent(
                    outlet_id=outlet.id,
                    respondent_name=respondent_name,
                    respondent_role=respondent_role,
                    phone=''
                )
                db.add(respondent)
                db.flush()
                print(f"   ✅ Created respondent: {respondent_name}")

            # Check if response already exists
            existing = db.query(Response).filter(
                Response.kobo_submission_id == kobo_id
            ).first()

            if existing:
                print(f"   ⏭️  Skipping (already synced)")
                continue

            # Create response
            response = Response(
                outlet_id=outlet.id,
                respondent_id=respondent.id,
                kobo_submission_id=kobo_id,
                accuracy_score=float(accuracy),
                verification_score=float(verification),
                independence_score=float(independence),
                fair_balanced_score=float(fair_balanced),
                public_interest_score=float(public_interest),
                corrections_score=float(corrections),
                raw_response_data=json.dumps(sub)
            )
            db.add(response)
            synced += 1
            print(f"   ✅ Synced response")

        except Exception as e:
            print(f"   ❌ Error: {e}")
            db.rollback()
            continue

    # Commit all changes
    db.commit()

    # Calculate MTI for all outlets
    outlets = db.query(Outlet).all()
    for outlet in outlets:
        responses = db.query(Response).filter(Response.outlet_id == outlet.id).all()
        if responses:
            n = len(responses)
            avg_accuracy = sum(r.accuracy_score for r in responses) / n
            avg_verification = sum(r.verification_score for r in responses) / n
            avg_independence = sum(r.independence_score for r in responses) / n
            avg_fair_balanced = sum(r.fair_balanced_score for r in responses) / n
            avg_public_interest = sum(r.public_interest_score for r in responses) / n
            avg_corrections = sum(r.corrections_score for r in responses) / n

            mti_score = (
                avg_accuracy * 0.20 +
                avg_verification * 0.20 +
                avg_independence * 0.20 +
                avg_fair_balanced * 0.15 +
                avg_public_interest * 0.15 +
                avg_corrections * 0.10
            )

            mti_index = db.query(MTIIndex).filter(MTIIndex.outlet_id == outlet.id).first()
            if mti_index:
                mti_index.mti_score = round(mti_score, 2)
            else:
                mti_index = MTIIndex(outlet_id=outlet.id, mti_score=round(mti_score, 2))
                db.add(mti_index)

            print(f"\n📊 {outlet.outlet_name} - MTI Score: {round(mti_score, 2)}")

    db.commit()
    db.close()

    print(f"\n🎉 Sync complete! {synced} responses saved.")

if __name__ == "__main__":
    print("🚀 Starting KoboToolkit sync...\n")
    sync_kobo_responses()