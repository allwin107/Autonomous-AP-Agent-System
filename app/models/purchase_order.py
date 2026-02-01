from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import Field
from app.models.base import MongoModel
from app.models.invoice import LineItem

class POStatus(str, Enum):
    DRAFT = "DRAFT"
    ISSUED = "ISSUED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    PARTIALLY_RECEIVED = "PARTIALLY_RECEIVED"
    RECEIVED = "RECEIVED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"

class PurchaseOrder(MongoModel):
    """
    Purchase Order document for 3-way matching.
    """
    po_number: str = Field(..., description="Unique PO number")
    company_id: str
    
    vendor_id: str
    vendor_name: str
    
    requester_email: str
    department: str
    cost_center: Optional[str] = None
    
    po_date: datetime
    delivery_date: Optional[datetime] = None
    
    line_items: List[LineItem] = []
    
    subtotal: float
    vat_amount: float
    total: float
    currency: str = "GBP"
    
    status: POStatus = Field(default=POStatus.ISSUED)
    
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def calculate_remaining_balance(self, invoiced_amount: float) -> float:
        """Calculate remaining budget on this PO."""
        return max(0.0, self.total - invoiced_amount)
