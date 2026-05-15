from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class Outlet(Base):
    """Table: Media outlets"""
    __tablename__ = "outlets"

    id = Column(Integer, primary_key=True, index=True)
    outlet_name = Column(String(255), unique=True, index=True)
    outlet_type = Column(String(100))  # TV, Radio, Online, Print
    region = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    respondents = relationship("Respondent", back_populates="outlet")
    responses = relationship("Response", back_populates="outlet")

class Respondent(Base):
    """Table: Survey respondents"""
    __tablename__ = "respondents"

    id = Column(Integer, primary_key=True, index=True)
    outlet_id = Column(Integer, ForeignKey("outlets.id"))
    respondent_name = Column(String(255))
    respondent_role = Column(String(255))  # Editor, Producer, etc.
    phone = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    outlet = relationship("Outlet", back_populates="respondents")
    responses = relationship("Response", back_populates="respondent")

class Response(Base):
    """Table: Survey responses from Kobo"""
    __tablename__ = "responses"

    id = Column(Integer, primary_key=True, index=True)
    outlet_id = Column(Integer, ForeignKey("outlets.id"))
    respondent_id = Column(Integer, ForeignKey("respondents.id"))
    kobo_submission_id = Column(String(255), unique=True, index=True)  # From Kobo API

    # MTI Dimensions (scores 0-100)
    accuracy_score = Column(Float, default=0.0)
    verification_score = Column(Float, default=0.0)
    independence_score = Column(Float, default=0.0)
    fair_balanced_score = Column(Float, default=0.0)
    public_interest_score = Column(Float, default=0.0)
    corrections_score = Column(Float, default=0.0)

    raw_response_data = Column(Text)  # JSON from Kobo
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    outlet = relationship("Outlet", back_populates="responses")
    respondent = relationship("Respondent", back_populates="responses")

class MTIIndex(Base):
    """Table: Calculated MTI Index per outlet"""
    __tablename__ = "mti_indices"

    id = Column(Integer, primary_key=True, index=True)
    outlet_id = Column(Integer, ForeignKey("outlets.id"), unique=True)
    mti_score = Column(Float)  # Overall MTI score (0-100)
    accuracy_weight = Column(Float, default=0.20)
    verification_weight = Column(Float, default=0.20)
    independence_weight = Column(Float, default=0.20)
    fair_balanced_weight = Column(Float, default=0.15)
    public_interest_weight = Column(Float, default=0.15)
    corrections_weight = Column(Float, default=0.10)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)