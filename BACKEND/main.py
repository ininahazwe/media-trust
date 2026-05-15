from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func
import json

from database import engine, get_db, Base
from models import Outlet, Respondent, Response, MTIIndex

# Créer les tables si elles n'existent pas
Base.metadata.create_all(bind=engine)

# Initialiser FastAPI
app = FastAPI(
    title="MFWA MTI Backend",
    description="Media Trust Barometer API",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# HEALTH CHECK
# ============================================
@app.get("/health")
def health_check():
    return {"status": "ok", "service": "MFWA MTI Backend"}

# ============================================
# OUTLETS ENDPOINTS
# ============================================
@app.post("/api/outlets")
def create_outlet(data: dict, db: Session = Depends(get_db)):
    """Créer un nouveau média"""
    try:
        outlet = Outlet(
            outlet_name=data.get("outlet_name"),
            outlet_type=data.get("outlet_type"),
            region=data.get("region")
        )
        db.add(outlet)
        db.commit()
        db.refresh(outlet)
        return {
            "id": outlet.id,
            "outlet_name": outlet.outlet_name,
            "outlet_type": outlet.outlet_type,
            "region": outlet.region,
            "created_at": outlet.created_at.isoformat()
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/outlets")
def list_outlets(db: Session = Depends(get_db)):
    """Lister tous les médias"""
    outlets = db.query(Outlet).all()
    return [{
        "id": o.id,
        "outlet_name": o.outlet_name,
        "outlet_type": o.outlet_type,
        "region": o.region,
        "created_at": o.created_at.isoformat()
    } for o in outlets]

@app.get("/api/outlets/{outlet_id}")
def get_outlet(outlet_id: int, db: Session = Depends(get_db)):
    """Récupérer un média par ID"""
    outlet = db.query(Outlet).filter(Outlet.id == outlet_id).first()
    if not outlet:
        raise HTTPException(status_code=404, detail="Outlet not found")
    return {
        "id": outlet.id,
        "outlet_name": outlet.outlet_name,
        "outlet_type": outlet.outlet_type,
        "region": outlet.region,
        "created_at": outlet.created_at.isoformat()
    }

# ============================================
# RESPONDENTS ENDPOINTS
# ============================================
@app.post("/api/respondents")
def create_respondent(data: dict, db: Session = Depends(get_db)):
    """Créer un nouveau répondant"""
    try:
        respondent = Respondent(
            outlet_id=data.get("outlet_id"),
            respondent_name=data.get("respondent_name"),
            respondent_role=data.get("respondent_role"),
            phone=data.get("phone")
        )
        db.add(respondent)
        db.commit()
        db.refresh(respondent)
        return {
            "id": respondent.id,
            "outlet_id": respondent.outlet_id,
            "respondent_name": respondent.respondent_name,
            "respondent_role": respondent.respondent_role,
            "phone": respondent.phone,
            "created_at": respondent.created_at.isoformat()
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/respondents")
def list_respondents(db: Session = Depends(get_db)):
    """Lister tous les répondants"""
    respondents = db.query(Respondent).all()
    return [{
        "id": r.id,
        "outlet_id": r.outlet_id,
        "respondent_name": r.respondent_name,
        "respondent_role": r.respondent_role,
        "phone": r.phone,
        "created_at": r.created_at.isoformat()
    } for r in respondents]

# ============================================
# RESPONSES ENDPOINTS
# ============================================
@app.post("/api/responses")
def create_response(data: dict, db: Session = Depends(get_db)):
    """Créer une nouvelle réponse de survey"""
    try:
        response = Response(
            outlet_id=data.get("outlet_id"),
            respondent_id=data.get("respondent_id"),
            kobo_submission_id=data.get("kobo_submission_id"),
            accuracy_score=float(data.get("accuracy_score", 0)),
            verification_score=float(data.get("verification_score", 0)),
            independence_score=float(data.get("independence_score", 0)),
            fair_balanced_score=float(data.get("fair_balanced_score", 0)),
            public_interest_score=float(data.get("public_interest_score", 0)),
            corrections_score=float(data.get("corrections_score", 0)),
            raw_response_data=data.get("raw_response_data", "{}")
        )
        db.add(response)
        db.commit()
        db.refresh(response)
        return {
            "id": response.id,
            "outlet_id": response.outlet_id,
            "respondent_id": response.respondent_id,
            "kobo_submission_id": response.kobo_submission_id,
            "accuracy_score": response.accuracy_score,
            "verification_score": response.verification_score,
            "independence_score": response.independence_score,
            "fair_balanced_score": response.fair_balanced_score,
            "public_interest_score": response.public_interest_score,
            "corrections_score": response.corrections_score,
            "created_at": response.created_at.isoformat()
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/responses")
def list_responses(db: Session = Depends(get_db)):
    """Lister toutes les réponses"""
    responses = db.query(Response).all()
    return [{
        "id": r.id,
        "outlet_id": r.outlet_id,
        "respondent_id": r.respondent_id,
        "kobo_submission_id": r.kobo_submission_id,
        "accuracy_score": r.accuracy_score,
        "verification_score": r.verification_score,
        "independence_score": r.independence_score,
        "fair_balanced_score": r.fair_balanced_score,
        "public_interest_score": r.public_interest_score,
        "corrections_score": r.corrections_score,
        "created_at": r.created_at.isoformat()
    } for r in responses]

# ============================================
# MTI CALCULATION
# ============================================
def calculate_mti_for_outlet(outlet_id: int, db: Session):
    """Calculer le score MTI pour un média"""
    responses = db.query(Response).filter(Response.outlet_id == outlet_id).all()

    if not responses:
        return None

    avg_accuracy = sum(r.accuracy_score for r in responses) / len(responses)
    avg_verification = sum(r.verification_score for r in responses) / len(responses)
    avg_independence = sum(r.independence_score for r in responses) / len(responses)
    avg_fair_balanced = sum(r.fair_balanced_score for r in responses) / len(responses)
    avg_public_interest = sum(r.public_interest_score for r in responses) / len(responses)
    avg_corrections = sum(r.corrections_score for r in responses) / len(responses)

    mti_score = (
        avg_accuracy * 0.20 +
        avg_verification * 0.20 +
        avg_independence * 0.20 +
        avg_fair_balanced * 0.15 +
        avg_public_interest * 0.15 +
        avg_corrections * 0.10
    )

    return {
        "mti_score": round(mti_score, 2),
        "accuracy": round(avg_accuracy, 2),
        "verification": round(avg_verification, 2),
        "independence": round(avg_independence, 2),
        "fair_balanced": round(avg_fair_balanced, 2),
        "public_interest": round(avg_public_interest, 2),
        "corrections": round(avg_corrections, 2),
    }

@app.post("/api/mti/calculate/{outlet_id}")
def calculate_mti(outlet_id: int, db: Session = Depends(get_db)):
    """Calculer et sauvegarder le MTI pour un outlet"""
    outlet = db.query(Outlet).filter(Outlet.id == outlet_id).first()
    if not outlet:
        raise HTTPException(status_code=404, detail="Outlet not found")

    mti_data = calculate_mti_for_outlet(outlet_id, db)
    if not mti_data:
        raise HTTPException(status_code=400, detail="No responses for this outlet")

    mti_index = db.query(MTIIndex).filter(MTIIndex.outlet_id == outlet_id).first()
    if mti_index:
        mti_index.mti_score = mti_data["mti_score"]
    else:
        mti_index = MTIIndex(outlet_id=outlet_id, mti_score=mti_data["mti_score"])
        db.add(mti_index)

    db.commit()
    db.refresh(mti_index)
    return mti_data

# ============================================
# DASHBOARD
# ============================================
@app.get("/api/dashboard")
def get_dashboard(db: Session = Depends(get_db)):
    """Récupérer les statistiques du dashboard"""
    total_outlets = db.query(func.count(Outlet.id)).scalar() or 0
    total_respondents = db.query(func.count(Respondent.id)).scalar() or 0
    total_responses = db.query(func.count(Response.id)).scalar() or 0

    top_outlets = db.query(
        Outlet.outlet_name,
        MTIIndex.mti_score
    ).join(MTIIndex).order_by(MTIIndex.mti_score.desc()).limit(5).all()

    avg_mti = db.query(func.avg(MTIIndex.mti_score)).scalar() or 0.0

    return {
        "total_outlets": total_outlets,
        "total_respondents": total_respondents,
        "total_responses": total_responses,
        "top_outlets": [{"name": o[0], "score": float(o[1]) if o[1] else 0} for o in top_outlets],
        "average_mti": round(float(avg_mti), 2) if avg_mti else 0.0
    }

# ============================================
# KOBO INTEGRATION
# ============================================
@app.get("/api/kobo/status")
def check_kobo_connection():
    """Vérifier la connexion à KoboToolkit"""
    try:
        from kobo_service import kobo_service
        forms = kobo_service.get_forms()
        if isinstance(forms, list):
            return {"status": "connected", "forms_count": len(forms)}
        return {"status": "error", "message": "Could not connect to Kobo"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)