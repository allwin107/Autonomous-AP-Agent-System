import asyncio
import os
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient

# Configuration
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://root:example@localhost:27017")
DB_NAME = os.getenv("DB_NAME", "ai_ap_system")

async def seed_db():
    print(f"Connecting to {MONGODB_URL}...")
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client[DB_NAME]
    
    company_id = "acme_corp"
    
    # 1. Company Config
    print("Seeding Company Config...")
    await db.company_config.update_one(
        {"company_id": company_id},
        {"$set": {
            "company_id": company_id,
            "company_name": "Acme Corporation",
            "currency": "GBP",
            "validation_rules": {
                "max_invoice_amount": 50000.0,
                "vat_tolerance": 0.05,
                "approved_vendors_only": True
            },
            "approval_matrix": [
                {"amount_min": 0, "amount_max": 1000, "approvers": ["manager"]},
                {"amount_min": 1000, "amount_max": None, "approvers": ["manager", "finance_director"]}
            ]
        }},
        upsert=True
    )
    
    # 2. Vendors
    print("Seeding Vendors...")
    vendors = [
        {
            "vendor_id": "V001",
            "company_id": company_id,
            "name": "Office Supplies Co",
            "bank_details": {
                "account_name": "Office Supplies Co",
                "account_number": "12345678",
                "sort_code": "00-00-00",
                "status": "VERIFIED"
            },
            "approval_status": "APPROVED"
        },
        {
            "vendor_id": "V002",
            "company_id": company_id,
            "name": "Tech Gadgets Ltd",
            "bank_details": {
                "account_name": "Tech Gadgets Ltd",
                "account_number": "87654321",
                "sort_code": "11-11-11",
                "status": "VERIFIED"
            },
            "approval_status": "APPROVED"
        }
    ]
    
    for v in vendors:
        await db.vendors.update_one(
            {"vendor_id": v["vendor_id"]},
            {"$set": v},
            upsert=True
        )

    # 3. Purchase Orders
    print("Seeding POs...")
    pos = [
        {
            "po_number": "PO-1001",
            "company_id": company_id,
            "vendor_id": "V001",
            "vendor_name": "Office Supplies Co",
            "requester": "john.doe@acme.com",
            "department": "IT",
            "po_date": datetime.utcnow(),
            "status": "issued",
            "subtotal": 500.0,
            "vat": 100.0,
            "total": 600.0
        }
    ]
    
    for po in pos:
        await db.purchase_orders.update_one(
            {"po_number": po["po_number"]},
            {"$set": po},
            upsert=True
        )

    print("Database seeding complete.")
    client.close()

if __name__ == "__main__":
    asyncio.run(seed_db())
