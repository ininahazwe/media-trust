"""
routers/respondents.py - Gestion des répondants
GET, POST, PUT, DELETE
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Respondent, Outlet
from schemas import RespondentCreate, RespondentResponse

router = APIRouter(prefix="/api/respondents", tags=["respondents"])

# ✅ GET ALL RESPONDENTS
@router.get("/", response_model=list[RespondentResponse])
async def get_all_respondents(db: Session = Depends(get_db)):
    """
    Récupère tous les répondants
    """
    respondents = db.query(Respondent).all()
    return respondents


# ✅ GET RESPONDENT BY ID
@router.get("/{respondent_id}", response_model=RespondentResponse)
async def get_respondent(respondent_id: int, db: Session = Depends(get_db)):
    """
    Récupère les détails d'un répondant
    """
    respondent = db.query(Respondent).filter(
        Respondent.id == respondent_id
    ).first()

    if not respondent:
        raise HTTPException(status_code=404, detail="Respondent not found")

    return respondent


# ✅ CREATE RESPONDENT
@router.post("/", response_model=RespondentResponse)
async def create_respondent(
    respondent: RespondentCreate,
    db: Session = Depends(get_db)
):
    """
    Crée un nouveau répondant pour un outlet
    """
    # Vérifier que l'outlet existe
    outlet = db.query(Outlet).filter(
        Outlet.id == respondent.outlet_id
    ).first()

    if not outlet:
        raise HTTPException(status_code=404, detail="Outlet not found")

    # Créer le répondant
    db_respondent = Respondent(
        outlet_id=respondent.outlet_id,
        respondent_name=respondent.respondent_name,
        respondent_role=respondent.respondent_role,
        phone=respondent.phone or ""
    )

    db.add(db_respondent)
    db.commit()
    db.refresh(db_respondent)

    return db_respondent


# ✅ UPDATE RESPONDENT
@router.put("/{respondent_id}", response_model=RespondentResponse)
async def update_respondent(
    respondent_id: int,
    respondent: RespondentCreate,
    db: Session = Depends(get_db)
):
    """
    Modifie un répondant existant
    """
    db_respondent = db.query(Respondent).filter(
        Respondent.id == respondent_id
    ).first()

    if not db_respondent:
        raise HTTPException(status_code=404, detail="Respondent not found")

    # Vérifier que le nouvel outlet existe
    outlet = db.query(Outlet).filter(
        Outlet.id == respondent.outlet_id
    ).first()

    if not outlet:
        raise HTTPException(status_code=404, detail="Outlet not found")

    # Mettre à jour
    db_respondent.outlet_id = respondent.outlet_id
    db_respondent.respondent_name = respondent.respondent_name
    db_respondent.respondent_role = respondent.respondent_role
    db_respondent.phone = respondent.phone or ""

    db.commit()
    db.refresh(db_respondent)

    return db_respondent


# ✅ DELETE RESPONDENT
@router.delete("/{respondent_id}")
async def delete_respondent(respondent_id: int, db: Session = Depends(get_db)):
    """
    Supprime un répondant
    ⚠️ Supprime aussi les responses associées
    """
    db_respondent = db.query(Respondent).filter(
        Respondent.id == respondent_id
    ).first()

    if not db_respondent:
        raise HTTPException(status_code=404, detail="Respondent not found")

    db.delete(db_respondent)
    db.commit()

    return {
        "message": "Respondent deleted successfully",
        "respondent_id": respondent_id
    }


# ✅ GET RESPONDENTS BY OUTLET
@router.get("/outlet/{outlet_id}")
async def get_respondents_by_outlet(
    outlet_id: int,
    db: Session = Depends(get_db)
):
    """
    Récupère tous les répondants d'un outlet
    """
    outlet = db.query(Outlet).filter(Outlet.id == outlet_id).first()

    if not outlet:
        raise HTTPException(status_code=404, detail="Outlet not found")

    respondents = db.query(Respondent).filter(
        Respondent.outlet_id == outlet_id
    ).all()

    return {
        "outlet_id": outlet_id,
        "outlet_name": outlet.outlet_name,
        "total_respondents": len(respondents),
        "respondents": respondents
    }


# ✅ GET RESPONDENT RESPONSES
@router.get("/{respondent_id}/responses")
async def get_respondent_responses(
    respondent_id: int,
    db: Session = Depends(get_db)
):
    """
    Récupère toutes les réponses d'un répondant
    """
    from models import Response

    respondent = db.query(Respondent).filter(
        Respondent.id == respondent_id
    ).first()

    if not respondent:
        raise HTTPException(status_code=404, detail="Respondent not found")

    responses = db.query(Response).filter(
        Response.respondent_id == respondent_id
    ).all()

    return {
        "respondent_id": respondent_id,
        "respondent_name": respondent.respondent_name,
        "total_responses": len(responses),
        "responses": responses
    }