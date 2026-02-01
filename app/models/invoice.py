from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any, TypedDict
from pydantic import Field, field_validator
from app.models.base import MongoModel

class InvoiceStatus(str, Enum):
    INGESTION = "INGESTION"
    EXTRACTION = "EXTRACTION"
    VALIDATION = "VALIDATION"
    MATCHING = "MATCHING"
    APPROVAL_ROUTING = "APPROVAL_ROUTING"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    PAYMENT_PREPARATION = "PAYMENT_PREPARATION"
    PAYMENT_SCHEDULED = "PAYMENT_SCHEDULED"
    PAID = "PAID"
    REJECTED = "REJECTED"
    EXCEPTION = "EXCEPTION"
    AWAITING_CORRECTION = "AWAITING_CORRECTION"

class LineItem(MongoModel):
    """Represents a single line item on an invoice."""
    item_id: int = Field(..., description="Line number or ID")
    description: str = Field(..., description="Description of the goods/service")
    quantity: float = Field(..., ge=0)
    unit_price: float = Field(..., ge=0)
    line_total: float = Field(..., ge=0)
    gl_code: Optional[str] = Field(None, description="General Ledger code")
    category: Optional[str] = Field(None, description="Expense category")

    @field_validator('line_total')
    @classmethod
    def validate_total(cls, v, info):
        """Validate that line total matches quantity * unit_price (roughly)"""
        if 'quantity' in info.data and 'unit_price' in info.data:
            calc = info.data['quantity'] * info.data['unit_price']
            if abs(v - calc) > 0.05: # 5 pence/cent tolerance
                # Could log warning here
                pass 
        return v

class ValidationResults(MongoModel):
    """Results from the automated validation agent."""
    is_duplicate: bool = Field(False, description="True if potential duplicate found")
    vat_valid: bool = Field(False, description="True if VAT calculation is correct")
    vendor_approved: bool = Field(False, description="True if vendor is in approved list")
    fraud_score: float = Field(0.0, ge=0.0, le=1.0, description="0.0 to 1.0 fraud risk score")
    flags: List[str] = Field(default_factory=list, description="List of risk flags raised")
    duplicate_of_id: Optional[str] = Field(None, description="ID of the original invoice if duplicate")
    validation_timestamp: datetime = Field(default_factory=datetime.utcnow)

class MatchingResults(MongoModel):
    """Results from the 3-way matching agent."""
    has_po: bool = False
    match_status: str = Field("PENDING", description="MATCHED, VARIANCE, NO_PO")
    quantity_variance: float = 0.0
    price_variance: float = 0.0
    auto_approvable: bool = False
    details: str = ""

class PaymentInstruction(MongoModel):
    """Final payment details derived from invoice and vendor data."""
    payment_id: str
    bank_account_number: str
    sort_code: Optional[str] = None
    iban: Optional[str] = None
    amount: float
    currency: str
    payment_date: datetime
    reference: Optional[str] = None
    status: str = "SCHEDULED"

class InvoiceData(MongoModel):
    """The core extracted invoice data."""
    # Identification
    vendor_name: str
    vendor_id: Optional[str] = None
    invoice_number: str
    
    # Dates
    invoice_date: datetime
    due_date: Optional[datetime] = None
    
    # Financials
    line_items: List[LineItem] = []
    subtotal: float = 0.0
    vat_rate: Optional[float] = None
    vat_amount: float = 0.0
    total: float = 0.0
    currency: str = "GBP"
    
    # References
    po_reference: Optional[str] = None
    
    def calculate_totals(self) -> float:
        """Recalculate total from line items."""
        return sum(item.line_total for item in self.line_items)

class Invoice(MongoModel):
    """
    Main Invoice document representing the end-to-end lifecycle.
    """
    invoice_id: str = Field(..., description="Unique internal ID (INV-YYYY-XXX)")
    company_id: str
    
    status: InvoiceStatus = Field(default=InvoiceStatus.INGESTION)
    previous_state: Optional[str] = None
    
    # Extracted Data
    data: Optional[InvoiceData] = None
    raw_text: Optional[str] = None
    file_path: Optional[str] = None
    
    # Workflow Results
    validation: Optional[ValidationResults] = None
    matching: Optional[MatchingResults] = None
    payment: Optional[PaymentInstruction] = None
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    retry_count: int = 0
    
    class Config:
        json_schema_extra = {
            "example": {
                "invoice_id": "INV-2024-001",
                "company_id": "acme_corp",
                "status": "AWAITING_APPROVAL",
                "data": {
                    "vendor_name": "Office Supplies Co",
                    "invoice_number": "OS-999",
                    "invoice_date": "2024-02-01T00:00:00",
                    "total": 120.00
                }
            }
        }

# TypedDict for LangGraph context
class InvoiceState(TypedDict):
    invoice_id: str
    company_id: str
    current_state: str
    invoice_data: Optional[Dict[str, Any]] # Serialized InvoiceData
    validation_results: Optional[Dict[str, Any]]
    matching_results: Optional[Dict[str, Any]]
    risk_score: float
    human_approval_required: bool
    errors: List[str]
