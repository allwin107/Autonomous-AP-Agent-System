from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException
from app.api.auth import get_current_active_user, User
from app.monitoring.metrics import metrics_engine

router = APIRouter(prefix="/api/metrics", tags=["Monitoring"])

@router.get("/system")
async def get_system_metrics():
    """Get overall system health and status distribution."""
    try:
        # For demo, using a fixed company_id. In production, get from user profile.
        company_id = "acme_corp"
        return await metrics_engine.get_system_health(company_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/agents/{agent_id}")
async def get_agent_metrics(agent_id: str):
    """Get performance metrics for a specific agent."""
    try:
        company_id = "acme_corp"
        return await metrics_engine.get_agent_performance(agent_id, company_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/costs")
async def get_cost_metrics():
    """Get LLM API cost metrics."""
    try:
        company_id = "acme_corp"
        return await metrics_engine.get_cost_metrics(company_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sla")
async def get_sla_metrics():
    """Get SLA compliance distribution."""
    try:
        company_id = "acme_corp"
        return await metrics_engine.get_sla_compliance(company_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/fraud")
async def get_fraud_metrics():
    """Get fraud detection statistics."""
    try:
        company_id = "acme_corp"
        return await metrics_engine.get_fraud_metrics(company_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
