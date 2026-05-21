"""
routers/outlets.py - Gestion des outlets (médias)
GET, POST, PUT, DELETE + analytics
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Outlet, Response, MTIIndex
from schemas import OutletCreate, OutletResponse
from sqlalchemy import func

router = APIRouter(prefix="/api/outlets", tags=["outlets"])

# ✅ GET ALL OUTLETS
@router.get("/", response_model=list[OutletResponse])
async def get_all_outlets(db: Session = Depends(get_db)):
    """
    Récupère tous les outlets avec leurs scores MTI
    """
    outlets = db.query(Outlet).all()
    return outlets


# ✅ GET OUTLET BY ID
@router.get("/{outlet_id}", response_model=OutletResponse)
async def get_outlet(outlet_id: int, db: Session = Depends(get_db)):
    """
    Récupère les détails d'un outlet spécifique
    """
    outlet = db.query(Outlet).filter(Outlet.id == outlet_id).first()
    if not outlet:
        raise HTTPException(status_code=404, detail="Outlet not found")
    return outlet


# ✅ CREATE OUTLET
@router.post("/", response_model=OutletResponse)
async def create_outlet(outlet: OutletCreate, db: Session = Depends(get_db)):
    """
    Crée un nouvel outlet (média)
    """
    # Vérifier si outlet existe déjà
    existing = db.query(Outlet).filter(
        Outlet.outlet_name == outlet.outlet_name
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Outlet already exists")

    # Créer nouvel outlet
    db_outlet = Outlet(
        outlet_name=outlet.outlet_name,
        outlet_type=outlet.outlet_type,
        region=outlet.region
    )
    db.add(db_outlet)
    db.commit()
    db.refresh(db_outlet)
    return db_outlet


# ✅ UPDATE OUTLET
@router.put("/{outlet_id}", response_model=OutletResponse)
async def update_outlet(
    outlet_id: int,
    outlet: OutletCreate,
    db: Session = Depends(get_db)
):
    """
    Modifie un outlet existant
    """
    db_outlet = db.query(Outlet).filter(Outlet.id == outlet_id).first()
    if not db_outlet:
        raise HTTPException(status_code=404, detail="Outlet not found")

    db_outlet.outlet_name = outlet.outlet_name
    db_outlet.outlet_type = outlet.outlet_type
    db_outlet.region = outlet.region

    db.commit()
    db.refresh(db_outlet)
    return db_outlet


# ✅ DELETE OUTLET
@router.delete("/{outlet_id}")
async def delete_outlet(outlet_id: int, db: Session = Depends(get_db)):
    """
    Supprime un outlet
    ⚠️ Supprime aussi les respondents et responses associées
    """
    db_outlet = db.query(Outlet).filter(Outlet.id == outlet_id).first()
    if not db_outlet:
        raise HTTPException(status_code=404, detail="Outlet not found")

    db.delete(db_outlet)
    db.commit()

    return {"message": "Outlet deleted successfully", "outlet_id": outlet_id}


# ✅ GET RESPONSES FOR OUTLET
@router.get("/{outlet_id}/responses")
async def get_outlet_responses(outlet_id: int, db: Session = Depends(get_db)):
    """
    Récupère toutes les réponses pour un outlet
    """
    outlet = db.query(Outlet).filter(Outlet.id == outlet_id).first()
    if not outlet:
        raise HTTPException(status_code=404, detail="Outlet not found")

    responses = db.query(Response).filter(Response.outlet_id == outlet_id).all()

    return {
        "outlet_id": outlet_id,
        "outlet_name": outlet.outlet_name,
        "total_responses": len(responses),
        "responses": responses
    }


# ✅ GET MTI SCORE FOR OUTLET
@router.get("/{outlet_id}/mti")
async def get_outlet_mti(outlet_id: int, db: Session = Depends(get_db)):
    """
    Récupère le score MTI pour un outlet
    """
    outlet = db.query(Outlet).filter(Outlet.id == outlet_id).first()
    if not outlet:
        raise HTTPException(status_code=404, detail="Outlet not found")

    mti_index = db.query(MTIIndex).filter(MTIIndex.outlet_id == outlet_id).first()

    if not mti_index:
        return {
            "outlet_id": outlet_id,
            "outlet_name": outlet.outlet_name,
            "mti_score": None,
            "message": "No MTI calculated yet"
        }

    return {
        "outlet_id": outlet_id,
        "outlet_name": outlet.outlet_name,
        "mti_score": mti_index.mti_score,
        "last_updated": mti_index.last_updated
    }


# ✅ GET OUTLETS BY REGION
@router.get("/region/{region}")
async def get_outlets_by_region(region: str, db: Session = Depends(get_db)):
    """
    Récupère tous les outlets d'une région
    """
    outlets = db.query(Outlet).filter(Outlet.region == region).all()

    return {
        "region": region,
        "total": len(outlets),
        "outlets": outlets
    }