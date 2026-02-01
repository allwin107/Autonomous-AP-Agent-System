import argparse
from app.database import db
from datetime import datetime

async def configure_company(company_id: str):
    print(f"Configuring company: {company_id}")
    
    config = {
        "company_id": company_id,
        "matching_tolerance": {"price": 0.05, "quantity": 0.0},
        "approval_limits": {"manager": 1000, "senior_manager": 5000, "director": 10000},
        "sla_thresholds": {"warning": 4, "critical": 24}, # hours
        "updated_at": datetime.utcnow()
    }
    
    await db.config.collection.update_one(
        {"company_id": company_id},
        {"$set": config},
        upsert=True
    )
    print("Configuration updated successfully.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Configure Company AP Policies")
    parser.add_argument("--company", type=str, required=True, help="Company ID to configure")
    args = parser.parse_args()
    
    import asyncio
    db.connect()
    try:
        asyncio.run(configure_company(args.company))
    finally:
        db.close()
