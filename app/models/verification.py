from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import Field
from app.models.base import MongoModel

class VerificationStatus(str, Enum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    CFO_APPROVAL_NEEDED = "CFO_APPROVAL_NEEDED"

class VerificationMethod(str, Enum):
    EMAIL = "EMAIL"
    PHONE_CALLBACK = "PHONE_CALLBACK"
    MANUAL = "MANUAL"

class VerificationRequest(MongoModel):
    """Tracks a fraud verification process."""
    invoice_id: str
    vendor_id: str
    risk_level: str = "HIGH"
    reason: str
    
    email_verification_status: VerificationStatus = VerificationStatus.PENDING
    callback_verification_status: VerificationStatus = VerificationStatus.PENDING
    cfo_approval_status: VerificationStatus = VerificationStatus.PENDING
    
    overall_status: VerificationStatus = VerificationStatus.PENDING
    
    notes: List[str] = []
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    def is_fully_verified(self) -> bool:
        return (self.email_verification_status == VerificationStatus.VERIFIED and
                self.callback_verification_status == VerificationStatus.VERIFIED and
                self.cfo_approval_status == VerificationStatus.VERIFIED)
