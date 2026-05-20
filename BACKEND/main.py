from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import requests
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

app = FastAPI(
    title="MFWA MTI Dashboard API",
    version="1.0.0",
)

# CORS Configuration
frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        frontend_url,
        "http://localhost:3000",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# 📊 DUMMY DATA (Will be replaced by Kobo data)
# ============================================================

OUTLETS = [
    {
        "id": 1,
        "name": "CitiFM",
        "region": "Greater Accra",
        "type": "Radio",
        "mti_score": 49.0,
        "accuracy": 4,
        "verification": 3,
        "independence": 4,
        "fair_balanced": 3,
        "public_interest": 4,
        "corrections": 2,
    },
    {
        "id": 2,
        "name": "Joy FM",
        "region": "Greater Accra",
        "type": "Radio",
        "mti_score": 52.5,
        "accuracy": 4,
        "verification": 4,
        "independence": 4,
        "fair_balanced": 3,
        "public_interest": 4,
        "corrections": 2,
    },
    {
        "id": 3,
        "name": "Adom FM",
        "region": "Ashanti",
        "type": "Radio",
        "mti_score": 46.0,
        "accuracy": 3,
        "verification": 3,
        "independence": 4,
        "fair_balanced": 3,
        "public_interest": 3,
        "corrections": 1,
    },
]

RESPONSES = [
    # CitiFM responses
    {"id": 1, "outlet_id": 1, "respondent_id": 1, "dimension": "accuracy", "accuracy_score": 4},
    {"id": 2, "outlet_id": 1, "respondent_id": 1, "dimension": "verification", "verification_score": 3},
    {"id": 3, "outlet_id": 1, "respondent_id": 1, "dimension": "independence", "independence_score": 4},
    {"id": 4, "outlet_id": 1, "respondent_id": 1, "dimension": "fair_balanced", "fair_balanced_score": 3},
    {"id": 5, "outlet_id": 1, "respondent_id": 1, "dimension": "public_interest", "public_interest_score": 4},
    {"id": 6, "outlet_id": 1, "respondent_id": 1, "dimension": "corrections", "corrections_score": 2},

    # Joy FM responses
    {"id": 7, "outlet_id": 2, "respondent_id": 2, "dimension": "accuracy", "accuracy_score": 4},
    {"id": 8, "outlet_id": 2, "respondent_id": 2, "dimension": "verification", "verification_score": 4},
    {"id": 9, "outlet_id": 2, "respondent_id": 2, "dimension": "independence", "independence_score": 4},
    {"id": 10, "outlet_id": 2, "respondent_id": 2, "dimension": "fair_balanced", "fair_balanced_score": 3},
    {"id": 11, "outlet_id": 2, "respondent_id": 2, "dimension": "public_interest", "public_interest_score": 4},
    {"id": 12, "outlet_id": 2, "respondent_id": 2, "dimension": "corrections", "corrections_score": 2},

    # Adom FM responses
    {"id": 13, "outlet_id": 3, "respondent_id": 3, "dimension": "accuracy", "accuracy_score": 3},
    {"id": 14, "outlet_id": 3, "respondent_id": 3, "dimension": "verification", "verification_score": 3},
    {"id": 15, "outlet_id": 3, "respondent_id": 3, "dimension": "independence", "independence_score": 4},
    {"id": 16, "outlet_id": 3, "respondent_id": 3, "dimension": "fair_balanced", "fair_balanced_score": 3},
    {"id": 17, "outlet_id": 3, "respondent_id": 3, "dimension": "public_interest", "public_interest_score": 3},
    {"id": 18, "outlet_id": 3, "respondent_id": 3, "dimension": "corrections", "corrections_score": 1},
]

# ============================================================
# 🔌 ENDPOINTS
# ============================================================

@app.get("/")
async def root():
    return {"message": "MFWA MTI Dashboard API - v1.0"}

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "MFWA MTI API"}

# ✅ DASHBOARD ENDPOINT
@app.get("/api/dashboard")
async def get_dashboard():
    """Get dashboard overview with all required fields for frontend"""

    # Sort by mti_score descending
    sorted_outlets = sorted(OUTLETS, key=lambda x: x["mti_score"], reverse=True)

    # Convert to format expected by frontend (top_outlets with score field)
    top_outlets = [
        {
            "name": outlet["name"],
            "score": outlet["mti_score"],
            "region": outlet["region"],
            "id": outlet["id"],
        }
        for outlet in sorted_outlets
    ]

    # Calculate average MTI
    average_mti = sum(o["mti_score"] for o in OUTLETS) / len(OUTLETS) if OUTLETS else 0

    return {
        "outlets": OUTLETS,
        "top_outlets": top_outlets,
        "total_outlets": len(OUTLETS),
        "average_mti": average_mti,
        "average_mti_score": average_mti,
        "total_responses": len(RESPONSES),
        "total_respondents": len(set(r["respondent_id"] for r in RESPONSES)),
        "status": "ok"
    }

# ✅ OUTLETS ENDPOINT
@app.get("/api/outlets")
async def get_outlets():
    """Get all outlets"""
    sorted_outlets = sorted(OUTLETS, key=lambda x: x["mti_score"], reverse=True)
    return {
        "outlets": sorted_outlets,
        "total": len(OUTLETS)
    }

# ✅ RESPONSES ENDPOINT
@app.get("/api/responses")
async def get_responses():
    """Get all responses for dimension breakdown"""
    return {
        "responses": RESPONSES,
        "total": len(RESPONSES)
    }

# ✅ KOBO SYNC ENDPOINT
@app.get("/api/kobo/sync")
async def sync_kobo_data():
    """Sync submissions from Kobo Toolkit"""
    try:
        kobo_token = os.getenv("KOBO_TOKEN")
        kobo_base = os.getenv("KOBO_BASE_URL", "https://kc.kobotoolbox.org")
        form_uid = os.getenv("KOBO_FORM_UID")

        if not kobo_token or not form_uid:
            return {
                "error": "Missing Kobo credentials (KOBO_TOKEN or KOBO_FORM_UID)",
                "status": "failed",
                "message": "Add KOBO_TOKEN and KOBO_FORM_UID to .env file"
            }

        # Fetch submissions from Kobo
        url = f"{kobo_base}/api/v2/assets/{form_uid}/data/"
        headers = {"Authorization": f"Token {kobo_token}"}

        print(f"[KOBO] Syncing from: {url}")
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code != 200:
            return {
                "error": f"Kobo API error: {response.status_code}",
                "status": "failed",
                "details": response.text
            }

        data = response.json()
        submissions = data.get("results", [])

        print(f"[KOBO] Found {len(submissions)} submissions")

        # Process submissions
        processed = []
        for idx, sub in enumerate(submissions):
            # Extract relevant fields from Kobo submission
            # Adjust field names based on your Kobo form
            processed_sub = {
                "submission_id": sub.get("_id", idx),
                "outlet_id": sub.get("outlet_id", 1),
                "respondent_id": sub.get("respondent_id", idx + 1),
                "accuracy_score": float(sub.get("accuracy", 0) or 0),
                "verification_score": float(sub.get("verification", 0) or 0),
                "independence_score": float(sub.get("independence", 0) or 0),
                "fair_balanced_score": float(sub.get("fair_balanced", 0) or 0),
                "public_interest_score": float(sub.get("public_interest", 0) or 0),
                "corrections_score": float(sub.get("corrections", 0) or 0),
                "submission_date": sub.get("_submission_time", datetime.now().isoformat()),
            }
            processed.append(processed_sub)

        return {
            "status": "success",
            "submissions_synced": len(processed),
            "submissions": processed,
            "last_sync": datetime.now().isoformat()
        }

    except requests.exceptions.Timeout:
        return {
            "error": "Kobo API timeout",
            "status": "failed"
        }
    except requests.exceptions.ConnectionError:
        return {
            "error": "Cannot connect to Kobo API",
            "status": "failed"
        }
    except Exception as e:
        return {
            "error": str(e),
            "status": "failed"
        }

# ✅ OUTLETS BY ID
@app.get("/api/outlets/{outlet_id}")
async def get_outlet(outlet_id: int):
    """Get a specific outlet"""
    for outlet in OUTLETS:
        if outlet["id"] == outlet_id:
            return outlet
    return {"error": "Outlet not found"}

# ✅ RESPONDENTS ENDPOINT
@app.post("/api/respondents")
async def create_respondent(data: dict):
    """Create a new respondent"""
    return {
        "message": "Respondent created",
        "data": data
    }

@app.get("/api/respondents")
async def get_respondents():
    """Get all respondents"""
    return {
        "respondents": [
            {"id": 1, "name": "John Doe", "outlet_id": 1},
            {"id": 2, "name": "Jane Smith", "outlet_id": 2},
            {"id": 3, "name": "James Brown", "outlet_id": 3},
        ],
        "total": 3
    }

# ✅ TEST ENDPOINT
@app.get("/api/test")
async def test_endpoint():
    return {"message": "Backend is working!", "status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=True
    )