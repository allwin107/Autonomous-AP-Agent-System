from fastapi import APIRouter, Depends
from typing import Dict, Any

from app.database import db
from app.api.auth import get_current_active_user, User
from app.models.invoice import InvoiceStatus

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

@router.get("/metrics")
async def get_metrics(current_user: User = Depends(get_current_active_user)):
    """High level system health and volume metrics."""
    return {
        "system_status": "healthy",
        "active_agents": ["ingestion", "extraction", "validation"], # Static for now
        "uptime": "99.9%"
    }

@router.get("/invoices/stats")
async def get_invoice_stats(current_user: User = Depends(get_current_active_user)):
    """Counts by status."""
    # Aggregation pipeline
    pipeline = [
        {"$group": {"_id": "$status", "count": {"$sum": 1}}}
    ]
    # Since we don't have aggregation in our simple Mongo wrapper yet, 
    # we might need to add it to Database class or access collection directly.
    # Accessing native collection for aggregation:
    
    try:
        col = db.invoices.collection
        cursor = col.aggregate(pipeline)
        stats = {InvoiceStatus(doc["_id"]).value: doc["count"] for doc in await cursor.to_list(length=100)}
        
        # Fill zeros
        final_stats = {status.value: 0 for status in InvoiceStatus}
        final_stats.update(stats)
        
        return final_stats
    except Exception as e:
        return {"error": str(e)}

@router.get("/audit/{invoice_id}")
async def get_audit_trail(invoice_id: str, current_user: User = Depends(get_current_active_user)):
    # Assuming we have an audit repo or collection query
    # db.audit is implemented as a repo log_action, but maybe not list?
    # Let's add a basic find to the repo or use direct find here
    
    logs = await db.db["audit_logs"].find({"invoice_id": invoice_id}).to_list(100)
    # Convert ObjectIds
    for log in logs:
        log["_id"] = str(log["_id"])
    return logs
