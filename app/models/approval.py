from datetime import datetime
from typing import Optional, List
from pydantic import Field
from app.models.base import MongoModel

class ApprovalAction(MongoModel):
    approver: str
    action: str # APPROVE, REJECT
    reason: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ApprovalRequest(MongoModel):
    request_id: str
    invoice_id: str
    company_id: str
    
    required_approvers: List[str]
    current_status: str = "PENDING"
    
    actions: List[ApprovalAction] = []
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
