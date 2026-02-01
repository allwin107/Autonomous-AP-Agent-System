from datetime import datetime
from typing import List, Optional, Literal
from pydantic import Field
from app.models.base import MongoModel, PyObjectId

class LineItem(MongoModel):
    item_id: int
    description: str
    quantity: float
    unit_price: float
    line_total: float
    gl_code: Optional[str] = None
    category: Optional[str] = None

class ValidationResults(MongoModel):
    is_duplicate: bool = False
    vat_valid: bool = False
    vendor_approved: bool = False
    fraud_score: float = 0.0
    validation_timestamp: datetime = Field(default_factory=datetime.utcnow)
    messages: List[str] = []

class MatchingResults(MongoModel):
    has_po: bool = False
    match_status: str = "PENDING"
    quantity_variance: float = 0.0
    price_variance: float = 0.0
    auto_approvable: bool = False

class Invoice(MongoModel):
    # Identity
    invoice_id: str = Field(..., description="Unique internal ID (e.g. INV-2024-001)")
    company_id: str
    
    # Status
    status: str = "INGESTION" 
    current_state: str = "INGESTION"
    
    # Extracted Data
    vendor_name: str
    vendor_id: Optional[str] = None
    invoice_number: str
    invoice_date: datetime
    due_date: Optional[datetime] = None
    
    line_items: List[LineItem] = []
    
    subtotal: float = 0.0
    vat_rate: float = 0.0
    vat_amount: float = 0.0
    total: float = 0.0
    currency: str = "GBP"
    
    # References
    po_reference: Optional[str] = None
    grn_reference: Optional[str] = None
    
    # Results
    validation_results: Optional[ValidationResults] = None
    matching_results: Optional[MatchingResults] = None
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
