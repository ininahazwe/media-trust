from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool
import os
from dotenv import load_dotenv

load_dotenv()

# SQLite par défaut (local), ou MySQL via DATABASE_URL dans .env
database_url = os.getenv("DATABASE_URL")
if not database_url:
    database_url = "sqlite:///./mfwa_mti.db"

print(f"[DATABASE] Connecting to: {database_url.split('@')[0] if '@' in database_url else 'SQLite'}")

# Créer l'engine selon le type de BDD
if "sqlite" in database_url:
    engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
elif "mysql" in database_url:
    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        pool_recycle=3600,
    )
else:
    # Default SQLite
    engine = create_engine(
        "sqlite:///./mfwa_mti.db",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()