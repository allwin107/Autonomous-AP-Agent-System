from datetime import datetime
from typing import Optional, List
from pydantic import Field, EmailStr
from app.models.base import MongoModel

class VendorContact(MongoModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[dict] = None

class BankDetails(MongoModel):
    account_name: str
    account_number: str
    sort_code: Optional[str] = None
    iban: Optional[str] = None
    swift: Optional[str] = None
    bank_name: Optional[str] = None
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    verification_status: str = "UNVERIFIED"

class Vendor(MongoModel):
    vendor_id: str
    company_id: str
    
    name: str
    legal_name: Optional[str] = None
    vat_number: Optional[str] = None
    company_registration: Optional[str] = None
    
    contact: Optional[VendorContact] = None
    bank_details: Optional[BankDetails] = None
    
    approval_status: str = "PENDING"
    risk_score: float = 0.0
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
