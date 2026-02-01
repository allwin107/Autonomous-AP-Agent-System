import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, DESCENDING, IndexModel

# Configuration (Import from app config in real usage, hardcoded for script simplicity/independence)
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://root:example@localhost:27017")
DB_NAME = os.getenv("DB_NAME", "ai_ap_system")

async def init_db():
    print(f"Connecting to {MONGODB_URL}...")
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client[DB_NAME]
    
    # 1. Invoices Collection
    print("Creating indexes on 'invoices'...")
    await db.invoices.create_indexes([
        IndexModel([("invoice_id", ASCENDING)], unique=True),
        IndexModel([("company_id", ASCENDING), ("status", ASCENDING)]),
        IndexModel([("company_id", ASCENDING), ("vendor_name", ASCENDING)]),
        IndexModel([("company_id", ASCENDING), ("due_date", ASCENDING)]),
        IndexModel([("validation_results.is_duplicate", ASCENDING)]),
    ])
    
    # 2. Vendors Collection
    print("Creating indexes on 'vendors'...")
    await db.vendors.create_indexes([
        IndexModel([("vendor_id", ASCENDING)], unique=True),
        IndexModel([("company_id", ASCENDING), ("name", ASCENDING)]),
        IndexModel([("vat_number", ASCENDING)]),
    ])
    
    # 3. Purchase Orders Collection
    print("Creating indexes on 'purchase_orders'...")
    await db.purchase_orders.create_indexes([
        IndexModel([("po_number", ASCENDING)], unique=True),
        IndexModel([("company_id", ASCENDING), ("vendor_id", ASCENDING)]),
        IndexModel([("status", ASCENDING)]),
    ])
    
    # 4. GRN Collection
    print("Creating indexes on 'goods_receipt_notes'...")
    await db.goods_receipt_notes.create_indexes([
        IndexModel([("grn_number", ASCENDING)], unique=True),
        IndexModel([("po_reference", ASCENDING)]),
    ])
    
    # 5. Audit Log Collection
    print("Creating indexes on 'audit_log'...")
    await db.audit_log.create_indexes([
        IndexModel([("event_id", ASCENDING)], unique=True),
        IndexModel([("invoice_id", ASCENDING)]),
        IndexModel([("timestamp", DESCENDING)]),
        IndexModel([("event_type", ASCENDING)]),
    ])
    
    # 6. Company Config
    print("Creating indexes on 'company_config'...")
    await db.company_config.create_indexes([
        IndexModel([("company_id", ASCENDING)], unique=True),
    ])
    
    # 7. Memory Store (Vector Index)
    # Note: Mongo 7.0 supports vector search via Atlas Vector Search or specialized implementations.
    # For local Mongo, we simulate basic indexing. Real vector search often requires Atlas or a plugin.
    # We will just create a standard index on fields for now.
    print("Creating indexes on 'memory_store'...")
    await db.memory_store.create_indexes([
        IndexModel([("company_id", ASCENDING), ("memory_type", ASCENDING)]),
        # Vector embedding field 'embedding'
    ])
    
    # 8. Approval Requests
    print("Creating indexes on 'approval_requests'...")
    await db.approval_requests.create_indexes([
        IndexModel([("request_id", ASCENDING)], unique=True),
        IndexModel([("invoice_id", ASCENDING)]),
        IndexModel([("current_status", ASCENDING)]),
    ])

    print("Database initialization complete.")
    client.close()

if __name__ == "__main__":
    asyncio.run(init_db())
