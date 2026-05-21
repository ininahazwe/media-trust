"""
routers/dashboard.py - Dashboard stats, analytics et Kobo synchronization
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
from models import Outlet, Response, MTIIndex, Respondent
import requests
import os
from dotenv import load_dotenv
from datetime import datetime
import json

load_dotenv()

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

# ============================================================
# 📊 DASHBOARD STATS
# ============================================================

@router.get("/")
async def get_dashboard(db: Session = Depends(get_db)):
    """
    Récupère les stats globales du dashboard
    """
    # Compter les outlets, répondants, responses
    total_outlets = db.query(func.count(Outlet.id)).scalar() or 0
    total_respondents = db.query(func.count(Respondent.id)).scalar() or 0
    total_responses = db.query(func.count(Response.id)).scalar() or 0

    # Calculer la moyenne MTI
    mti_scores = db.query(MTIIndex.mti_score).all()
    average_mti = sum(s[0] for s in mti_scores) / len(mti_scores) if mti_scores else 0

    # Top outlets par score MTI
    top_outlets_query = db.query(
        Outlet.outlet_name,
        Outlet.region,
        MTIIndex.mti_score
    ).join(
        MTIIndex, Outlet.id == MTIIndex.outlet_id
    ).order_by(
        MTIIndex.mti_score.desc()
    ).limit(10).all()

    top_outlets = [
        {
            "name": outlet[0],
            "region": outlet[1],
            "score": round(outlet[2], 2) if outlet[2] else 0
        }
        for outlet in top_outlets_query
    ]

    return {
        "total_outlets": total_outlets,
        "total_respondents": total_respondents,
        "total_responses": total_responses,
        "average_mti": round(average_mti, 2),
        "top_outlets": top_outlets,
        "status": "ok"
    }


# ============================================================
# 📈 DIMENSIONS BREAKDOWN
# ============================================================

@router.get("/dimensions")
async def get_dimensions_breakdown(db: Session = Depends(get_db)):
    """
    Récupère les scores moyens par dimension MTI
    """
    responses = db.query(Response).all()

    if not responses:
        return {
            "accuracy": 0,
            "verification": 0,
            "independence": 0,
            "fair_balanced": 0,
            "public_interest": 0,
            "corrections": 0
        }

    n = len(responses)

    return {
        "accuracy": round(sum(r.accuracy_score for r in responses) / n, 2),
        "verification": round(sum(r.verification_score for r in responses) / n, 2),
        "independence": round(sum(r.independence_score for r in responses) / n, 2),
        "fair_balanced": round(sum(r.fair_balanced_score for r in responses) / n, 2),
        "public_interest": round(sum(r.public_interest_score for r in responses) / n, 2),
        "corrections": round(sum(r.corrections_score for r in responses) / n, 2)
    }


# ============================================================
# 🎯 MTI CALCULATION
# ============================================================

@router.post("/calculate-mti")
async def calculate_mti_for_all(db: Session = Depends(get_db)):
    """
    Recalcule les scores MTI pour tous les outlets
    Basé sur les réponses existantes
    """
    outlets = db.query(Outlet).all()
    updated_count = 0

    for outlet in outlets:
        responses = db.query(Response).filter(
            Response.outlet_id == outlet.id
        ).all()

        if not responses:
            continue

        n = len(responses)

        # Calculer les moyennes par dimension
        avg_accuracy = sum(r.accuracy_score for r in responses) / n
        avg_verification = sum(r.verification_score for r in responses) / n
        avg_independence = sum(r.independence_score for r in responses) / n
        avg_fair_balanced = sum(r.fair_balanced_score for r in responses) / n
        avg_public_interest = sum(r.public_interest_score for r in responses) / n
        avg_corrections = sum(r.corrections_score for r in responses) / n

        # Calculer le score MTI avec les poids
        mti_score = (
            avg_accuracy * 0.20 +
            avg_verification * 0.20 +
            avg_independence * 0.20 +
            avg_fair_balanced * 0.15 +
            avg_public_interest * 0.15 +
            avg_corrections * 0.10
        )

        # Chercher ou créer MTIIndex
        mti_index = db.query(MTIIndex).filter(
            MTIIndex.outlet_id == outlet.id
        ).first()

        if mti_index:
            mti_index.mti_score = round(mti_score, 2)
        else:
            mti_index = MTIIndex(
                outlet_id=outlet.id,
                mti_score=round(mti_score, 2)
            )
            db.add(mti_index)

        updated_count += 1

    db.commit()

    return {
        "status": "success",
        "message": f"MTI recalculated for {updated_count} outlets",
        "updated_outlets": updated_count
    }


# ============================================================
# 🔄 KOBO SYNCHRONIZATION
# ============================================================

@router.post("/sync-kobo")
async def sync_kobo_data(db: Session = Depends(get_db)):
    """
    Synchronise les submissions de Kobo vers SQLite
    """
    try:
        # Récupérer les credentials
        kobo_token = os.getenv("KOBO_TOKEN")
        form_uid = os.getenv("KOBO_FORM_UID", "aSSVtGFgeJti6Ln8KM5EzY")

        if not kobo_token:
            raise HTTPException(
                status_code=400,
                detail="KOBO_TOKEN not set in .env"
            )

        # Récupérer les submissions
        url = f"https://kf.kobotoolbox.org/api/v2/assets/{form_uid}/data/"
        headers = {"Authorization": f"Token {kobo_token}"}

        print(f"[KOBO] Syncing from: {url}")
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Kobo API error: {response.text}"
            )

        data = response.json()
        submissions = data.get("results", [])

        print(f"[KOBO] Found {len(submissions)} submissions")

        # Mapping des réponses Kobo vers scores
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
                return 50
            return RESPONSE_MAPPING.get(str(response_value).lower(), 50)

        synced = 0

        # Traiter chaque submission
        for sub in submissions:
            try:
                # Extraire les données
                outlet_name = sub.get('rating/outlet_name', 'Unknown')
                outlet_name = outlet_name.title() if outlet_name else 'Unknown'

                respondent_name = f"R{sub.get('_id', 'Unknown')}"
                respondent_role = "Survey Respondent"

                kobo_id = str(sub.get('_uuid', ''))

                # Extraire les scores MTI des réponses Kobo
                accuracy = kobo_response_to_score(
                    sub.get('rating/outlet_grp/outlet_accuracy')
                )
                verification = kobo_response_to_score(
                    sub.get('rating/outlet_grp/outlet_verify')
                )
                independence = kobo_response_to_score(
                    sub.get('rating/outlet_grp/outlet_indep')
                )
                fair_balanced = kobo_response_to_score(
                    sub.get('rating/outlet_grp/outlet_fair')
                )
                public_interest = kobo_response_to_score(
                    sub.get('rating/outlet_grp/outlet_public')
                )
                corrections = kobo_response_to_score(
                    sub.get('rating/outlet_grp/outlet_correct')
                )

                # Créer ou récupérer l'outlet
                outlet = db.query(Outlet).filter(
                    Outlet.outlet_name == outlet_name
                ).first()

                if not outlet:
                    outlet = Outlet(
                        outlet_name=outlet_name,
                        outlet_type="Radio",
                        region=sub.get('geo/region', 'Unknown')
                    )
                    db.add(outlet)
                    db.flush()

                # Créer ou récupérer le répondant
                respondent = db.query(Respondent).filter(
                    Respondent.outlet_id == outlet.id,
                    Respondent.respondent_name == respondent_name
                ).first()

                if not respondent:
                    respondent = Respondent(
                        outlet_id=outlet.id,
                        respondent_name=respondent_name,
                        respondent_role=respondent_role,
                        phone=""
                    )
                    db.add(respondent)
                    db.flush()

                # Vérifier si la réponse existe déjà
                existing = db.query(Response).filter(
                    Response.kobo_submission_id == kobo_id
                ).first()

                if existing:
                    continue

                # Créer la réponse
                response_obj = Response(
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
                db.add(response_obj)
                synced += 1

            except Exception as e:
                print(f"[KOBO] Error processing submission: {e}")
                db.rollback()
                continue

        # Commit all changes
        db.commit()

        # Recalculate MTI for all outlets
        await calculate_mti_for_all(db)

        return {
            "status": "success",
            "message": f"Synced {synced} new submissions from Kobo",
            "submissions_synced": synced,
            "last_sync": datetime.now().isoformat()
        }

    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="Kobo API timeout")
    except requests.exceptions.ConnectionError:
        raise HTTPException(
            status_code=503,
            detail="Cannot connect to Kobo API"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 🔍 OUTLETS DETAILS
# ============================================================

@router.get("/outlets-details")
async def get_outlets_details(db: Session = Depends(get_db)):
    """
    Récupère tous les outlets avec leurs scores MTI et stats
    """
    outlets = db.query(Outlet).all()

    outlets_data = []
    for outlet in outlets:
        mti_index = db.query(MTIIndex).filter(
            MTIIndex.outlet_id == outlet.id
        ).first()

        responses_count = db.query(func.count(Response.id)).filter(
            Response.outlet_id == outlet.id
        ).scalar() or 0

        respondents_count = db.query(func.count(Respondent.id)).filter(
            Respondent.outlet_id == outlet.id
        ).scalar() or 0

        outlets_data.append({
            "id": outlet.id,
            "name": outlet.outlet_name,
            "type": outlet.outlet_type,
            "region": outlet.region,
            "mti_score": mti_index.mti_score if mti_index else None,
            "responses_count": responses_count,
            "respondents_count": respondents_count,
            "created_at": outlet.created_at
        })

    return {
        "total": len(outlets_data),
        "outlets": sorted(outlets_data, key=lambda x: x["mti_score"] or 0, reverse=True)
    }