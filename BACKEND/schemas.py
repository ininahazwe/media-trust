from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional

class OutletCreate(BaseModel):
    outlet_name: str
    outlet_type: str
    region: str

class OutletResponse(OutletCreate):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class RespondentCreate(BaseModel):
    outlet_id: int
    respondent_name: str
    respondent_role: str
    phone: Optional[str] = None

class RespondentResponse(RespondentCreate):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

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

    model_config = ConfigDict(from_attributes=True)

class MTIIndexResponse(BaseModel):
    id: int
    outlet_id: int
    mti_score: float
    last_updated: datetime

    model_config = ConfigDict(from_attributes=True)

class DashboardStats(BaseModel):
    total_outlets: int
    total_respondents: int
    total_responses: int
    top_outlets: list
    average_mti: float