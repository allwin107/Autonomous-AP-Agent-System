from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Body

from app.database import db
from app.api.auth import get_admin_user, User
from app.models.config import CompanyConfig

router = APIRouter(prefix="/api/admin", tags=["Admin"])

@router.post("/companies", status_code=201)
async def onboard_company(
    config: CompanyConfig,
    current_user: User = Depends(get_admin_user)
):
    existing = await db.config.get_by_field("company_id", config.company_id)
    if existing:
        raise HTTPException(status_code=400, detail="Company already exists")
    
    await db.config.create(config)
    return {"message": "Company onboarded successfully", "company_id": config.company_id}

@router.get("/companies/{company_id}")
async def get_company_config(
    company_id: str,
    current_user: User = Depends(get_admin_user)
):
    config = await db.config.get_by_field("company_id", company_id)
    if not config:
        raise HTTPException(status_code=404, detail="Company config not found")
    return config

@router.put("/companies/{company_id}/config")
async def update_company_config(
    company_id: str,
    update_data: Dict[str, Any] = Body(...),
    current_user: User = Depends(get_admin_user)
):
    config = await db.config.get_by_field("company_id", company_id)
    if not config:
        raise HTTPException(status_code=404, detail="Company config not found")
    
    await db.config.update(company_id, update_data) # Note: repo update usually takes ID, check implementation
    # Config repo might need 'update_by_company_id' if ID is not _id
    
    return {"message": "Config updated"}
