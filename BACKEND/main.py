from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from database import engine, Base
from routers import outlets, respondents, dashboard

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="MFWA MTI Dashboard API",
    version="1.0.0",
    description="Media Trust Barometer API"
)

# CORS Configuration
frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        frontend_url,
        "http://localhost:3000",
        "http://localhost:5173",
        "https://votre-frontend.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "MFWA MTI API"}

# Import routes
app.include_router(outlets.router)
app.include_router(respondents.router)
app.include_router(dashboard.router)

@app.get("/")
async def root():
    return {"message": "MFWA MTI Dashboard API - v1.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=False
    )