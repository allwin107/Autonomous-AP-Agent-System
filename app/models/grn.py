from datetime import datetime
from typing import List, Optional
from pydantic import Field
from app.models.base import MongoModel

class GRNItem(MongoModel):
    item_id: int
    description: str
    quantity_ordered: float
    quantity_received: float
    quantity_accepted: float
    quantity_rejected: float = 0.0
    rejection_reason: Optional[str] = None

class GoodsReceiptNote(MongoModel):
    grn_number: str
    company_id: str
    po_reference: str
    vendor_id: str
    
    received_by: str
    received_date: datetime = Field(default_factory=datetime.utcnow)
    
    line_items: List[GRNItem] = []
    
    status: str = "COMPLETED"
    notes: Optional[str] = None
