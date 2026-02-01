from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.config import settings
from app.database import db

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    db.connect()
    yield
    # Shutdown
    db.close()

app = FastAPI(
    title="AI Accounts Payable Employee",
    description="Autonomous AI Agent System for Accounts Payable Automation",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "database": "connected" if db.client else "disconnected"
    }

@app.get("/")
async def root():
    return {
        "message": "Welcome to AI CA Employee System",
        "docs": "/docs"
    }
