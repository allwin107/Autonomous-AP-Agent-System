from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import Field
from app.models.base import MongoModel
from app.models.invoice import LineItem

class GRNStatus(str, Enum):
    RECEIVED = "RECEIVED"
    INSPECTED = "INSPECTED"
    RETURNED = "RETURNED"

class GoodsReceiptNote(MongoModel):
    """
    Goods Receipt Note (GRN) document.
    Represents physical receipt of goods against a PO.
    """
    grn_number: str = Field(..., description="Unique GRN ID")
    po_number: str = Field(..., description="Reference to PO")
    company_id: str
    vendor_id: str
    
    received_date: datetime = Field(default_factory=datetime.utcnow)
    received_by: str
    
    line_items: List[LineItem] = [] # Items received (quantity matters most here)
    
    status: GRNStatus = Field(default=GRNStatus.RECEIVED)
    
    delivery_note_ref: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
