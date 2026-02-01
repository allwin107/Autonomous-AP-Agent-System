import asyncio
import logging
from datetime import datetime, timedelta
from app.database import db
from app.models.invoice import InvoiceStatus
from app.agents.reflection import reflection_agent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_nightly_reflection():
    """
    Batch process reflection for all invoices handled in the last 24 hours.
    """
    logger.info("Starting nightly reflection batch job...")
    
    # 1. Identify invoices processed in the last 24h
    since = datetime.utcnow() - timedelta(days=1)
    
    # Find failures (Exception or Rejected)
    failure_query = {
        "status": {"$in": [InvoiceStatus.EXCEPTION, InvoiceStatus.REJECTED]},
        "updated_at": {"$gte": since}
    }
    
    failures = await db.db["invoices"].find(failure_query).to_list(None)
    logger.info(f"Found {len(failures)} failures to reflect on.")
    
    for doc in failures:
        invoice_id = doc["invoice_id"]
        status = doc["status"]
        await reflection_agent.reflect_on_failure(
            invoice_id, 
            failure_type=f"BATCH_REFLECTION_{status}",
            context="Nightly batch analysis"
        )
        
    # Find successes (Paid)
    success_query = {
        "status": InvoiceStatus.PAID,
        "updated_at": {"$gte": since}
    }
    successes = await db.db["invoices"].find(success_query).to_list(None)
    logger.info(f"Found {len(successes)} successes to reflect on.")
    
    for doc in successes:
        await reflection_agent.reflect_on_success(doc["invoice_id"])
        
    logger.info("Nightly reflection complete.")

if __name__ == "__main__":
    asyncio.run(run_nightly_reflection())
