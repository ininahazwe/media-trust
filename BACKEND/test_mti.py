#!/usr/bin/env python3
"""
Test endpoints and calculate MTI scores
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_kobo_connection():
    """Test Kobo API connection"""
    print("\n🔗 Testing Kobo connection...")
    r = requests.get(f"{BASE_URL}/api/kobo/status")
    print(f"Status: {r.json()}")
    return r.status_code == 200

def list_outlets():
    """List all outlets"""
    print("\n📋 Outlets in database:")
    r = requests.get(f"{BASE_URL}/api/outlets")
    outlets = r.json()
    for o in outlets:
        print(f"  ID {o['id']}: {o['outlet_name']} ({o['outlet_type']}) - {o['region']}")
    return outlets

def list_responses():
    """List all responses"""
    print("\n📊 Responses in database:")
    r = requests.get(f"{BASE_URL}/api/responses")
    responses = r.json()
    print(f"  Total responses: {len(responses)}")
    for r_item in responses[:5]:  # Show first 5
        print(f"    - Outlet {r_item['outlet_id']}: accuracy={r_item['accuracy_score']}")
    return responses

def calculate_mti_all(outlets):
    """Calculate MTI for all outlets"""
    print("\n🎯 Calculating MTI scores...")
    for outlet in outlets:
        outlet_id = outlet['id']
        print(f"  Calculating for {outlet['outlet_name']} (ID: {outlet_id})...", end=" ")
        r = requests.post(f"{BASE_URL}/api/mti/calculate/{outlet_id}")

        if r.status_code == 200:
            mti = r.json()
            print(f"✅ MTI: {mti['mti_score']}")
        else:
            print(f"❌ Error: {r.json().get('detail', 'Unknown')}")

def get_dashboard():
    """Get dashboard stats"""
    print("\n📊 Dashboard Stats:")
    r = requests.get(f"{BASE_URL}/api/dashboard")
    stats = r.json()

    print(f"  Total outlets: {stats['total_outlets']}")
    print(f"  Total respondents: {stats['total_respondents']}")
    print(f"  Total responses: {stats['total_responses']}")
    print(f"  Average MTI: {stats['average_mti']}")

    if stats['top_outlets']:
        print(f"\n  Top outlets by MTI:")
        for outlet in stats['top_outlets']:
            print(f"    - {outlet['name']}: {outlet['score']}")

    return stats

if __name__ == "__main__":
    print("=" * 60)
    print("MFWA MTI - Test & Calculate")
    print("=" * 60)

    # Test connection
    if not test_kobo_connection():
        print("❌ Could not connect to API")
        exit(1)

    # Get outlets
    outlets = list_outlets()

    if not outlets:
        print("\n⚠️  No outlets found. Sync Kobo data first!")
        exit(1)

    # List responses
    list_responses()

    # Calculate MTI
    calculate_mti_all(outlets)

    # Show dashboard
    get_dashboard()

    print("\n✅ Test complete!")