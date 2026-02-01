from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict
from pydantic import Field, EmailStr, HttpUrl
from app.models.base import MongoModel

class VerificationStatus(str, Enum):
    UNVERIFIED = "UNVERIFIED"
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"

class BankDetails(MongoModel):
    """Vendor bank account information."""
    account_name: str
    account_number: str
    sort_code: Optional[str] = None
    iban: Optional[str] = None
    swift: Optional[str] = None
    bank_name: Optional[str] = None
    
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    verification_status: VerificationStatus = Field(default=VerificationStatus.UNVERIFIED)
    verified_by: Optional[str] = None

class VendorRiskProfile(MongoModel):
    """Risk assessment for the vendor."""
    risk_score: float = Field(0.00, ge=0.0, le=1.0, description="0.0 (Safe) to 1.0 (High Risk)")
    fraud_history: List[str] = Field(default_factory=list, description="Records of past fraud attempts")
    last_assessment_date: datetime = Field(default_factory=datetime.utcnow)
    category: str = Field("STANDARD", description="LOW_RISK, STANDARD, HIGH_RISK")

class VendorContact(MongoModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    website: Optional[HttpUrl] = None
    address: Optional[Dict[str, str]] = None

class Vendor(MongoModel):
    """
    Vendor master data.
    """
    vendor_id: str = Field(..., description="Unique vendor ID")
    company_id: str
    
    name: str
    legal_name: Optional[str] = None
    vat_number: Optional[str] = None
    company_registration_number: Optional[str] = None
    
    contact: Optional[VendorContact] = None
    bank_details: Optional[BankDetails] = None
    risk_profile: VendorRiskProfile = Field(default_factory=VendorRiskProfile)
    
    payment_terms: str = Field("NET30", description="NET30, NET60, IMMEDIATE")
    approval_status: str = "APPROVED"
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
