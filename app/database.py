from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorGridFSBucket
from app.config import settings
from app.repositories.invoice import InvoiceRepository
from app.repositories.vendor import VendorRepository
from app.repositories.audit import AuditLogger
from app.repositories.config import ConfigRepository
from app.models.invoice import Invoice
from app.models.vendor import Vendor
from app.models.audit import AuditEvent
from app.models.config import CompanyConfig

class Database:
    client: AsyncIOMotorClient = None
    fs: AsyncIOMotorGridFSBucket = None
    
    # Repositories
    invoices: InvoiceRepository = None
    vendors: VendorRepository = None
    audit: AuditLogger = None
    config: ConfigRepository = None
    
    def connect(self):
        """Initialize database connection and repositories."""
        self.client = AsyncIOMotorClient(settings.MONGODB_URL)
        db = self.client[settings.DB_NAME]
        self.fs = AsyncIOMotorGridFSBucket(db)
        
        # Initialize repositories with their respective collections and models
        self.invoices = InvoiceRepository(db.invoices, Invoice)
        self.vendors = VendorRepository(db.vendors, Vendor)
        self.audit = AuditLogger(db.audit_log, AuditEvent)
        self.config = ConfigRepository(db.company_config, CompanyConfig)
        
        print("Connected to MongoDB")
        
    def close(self):
        """Close database connection."""
        if self.client:
            self.client.close()
            print("Disconnected from MongoDB")

db = Database()

async def get_db() -> Database:
    """Dependency for FastAPI."""
    return db
