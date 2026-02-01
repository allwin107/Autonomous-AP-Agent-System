from datetime import datetime
from typing import Optional, Any, Dict
from pydantic import Field
from app.models.base import MongoModel

class Actor(MongoModel):
    type: str # AGENT, USER, SYSTEM
    id: str
    name: str

class AuditLog(MongoModel):
    event_id: str
    invoice_id: Optional[str] = None
    company_id: str
    
    event_type: str
    event_category: str
    
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    actor: Actor
    
    action: str
    previous_state: Optional[str] = None
    new_state: Optional[str] = None
    
    details: Dict[str, Any] = {}
    decision: Optional[Dict[str, Any]] = None
