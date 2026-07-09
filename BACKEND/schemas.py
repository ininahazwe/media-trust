from pydantic import BaseModel
from datetime import datetime
from typing import Optional

# Le serveur de prod (cPanel, Python 3.6) est figé sur pydantic==1.9.2
# (pas de wheel pydantic v2 pour ce Python), alors que le dev local (Windows,
# Python 3.13) tourne en pydantic v2. On détecte la version disponible et on
# bascule sur la bonne syntaxe de config, pour ne plus avoir à retoucher ce
# fichier à chaque déploiement.
try:
    from pydantic import ConfigDict
    PYDANTIC_V2 = True
except ImportError:
    PYDANTIC_V2 = False

class OutletCreate(BaseModel):
    outlet_name: str
    outlet_type: str
    region: str

class OutletResponse(OutletCreate):
    id: int
    created_at: datetime

    if PYDANTIC_V2:
        model_config = ConfigDict(from_attributes=True)
    else:
        class Config:
            orm_mode = True

class RespondentCreate(BaseModel):
    outlet_id: int
    respondent_name: str
    respondent_role: str
    phone: Optional[str] = None

class RespondentResponse(RespondentCreate):
    id: int
    created_at: datetime

    if PYDANTIC_V2:
        model_config = ConfigDict(from_attributes=True)
    else:
        class Config:
            orm_mode = True

class ResponseCreate(BaseModel):
    outlet_id: int
    respondent_id: int
    kobo_submission_id: str
    accuracy_score: float
    verification_score: float
    independence_score: float
    fair_balanced_score: float
    public_interest_score: float
    corrections_score: float
    raw_response_data: str

class ResponseSchema(ResponseCreate):
    id: int
    created_at: datetime

    if PYDANTIC_V2:
        model_config = ConfigDict(from_attributes=True)
    else:
        class Config:
            orm_mode = True

class MTIIndexResponse(BaseModel):
    id: int
    outlet_id: int
    mti_score: float
    last_updated: datetime

    if PYDANTIC_V2:
        model_config = ConfigDict(from_attributes=True)
    else:
        class Config:
            orm_mode = True

class DashboardStats(BaseModel):
    total_outlets: int
    total_respondents: int
    total_responses: int
    top_outlets: list
    average_mti: float