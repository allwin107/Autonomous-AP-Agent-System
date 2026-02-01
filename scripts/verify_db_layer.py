import asyncio
from app.database import db

async def verify():
    print("Connecting to database...")
    db.connect()
    
    if db.client:
        print("✅ Client initialized")
    else:
        print("❌ Client NOT initialized")
        
    if db.invoices:
        print("✅ InvoiceRepository initialized")
    else:
        print("❌ InvoiceRepository NOT initialized")

    try:
        # Ping the database
        await db.client.admin.command('ping')
        print("✅ Database connection successful (Ping)")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        
    db.close()

if __name__ == "__main__":
    asyncio.run(verify())
