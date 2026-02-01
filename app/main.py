from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging

from app.config import settings
from app.api import invoices, approvals, dashboard, admin, auth, ui

# Setup Logging
logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI AP Employee API",
    description="Backend API for Autonomous Accounts Payable Agent",
    version="1.0.0"
)

# CORS Config
origins = [
    "http://localhost:3000",
    "http://localhost:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Router Registration
app.include_router(auth.router)
app.include_router(invoices.router)
app.include_router(approvals.router)
app.include_router(dashboard.router)
app.include_router(admin.router)
app.include_router(ui.router)

# Health Check
@app.get("/health")
async def health_check():
    return {"status": "ok", "environment": settings.ENVIRONMENT}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
