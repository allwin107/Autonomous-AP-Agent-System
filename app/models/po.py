from datetime import datetime
from typing import List, Optional
from pydantic import Field
from app.models.base import MongoModel

class POItem(MongoModel):
    item_id: int
    description: str
    quantity: float
    unit_price: float
    line_total: float
    gl_code: Optional[str] = None

class PurchaseOrder(MongoModel):
    po_number: str
    company_id: str
    vendor_id: str
    vendor_name: str
    
    requester: str
    department: str
    
    po_date: datetime
    delivery_date: Optional[datetime] = None
    
    line_items: List[POItem] = []
    
    subtotal: float
    vat: float
    total: float
    currency: str = "GBP"
    
    status: str = "ISSUED" # DRAFT, ISSUED, RECEIVED, CLOSED
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
