from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import Field
from app.models.base import MongoModel

class ActionType(str, Enum):
    SYSTEM_EVENT = "SYSTEM_EVENT"
    USER_ACTION = "USER_ACTION"
    AGENT_DECISION = "AGENT_DECISION"
    API_CALL = "API_CALL"
    ERROR = "ERROR"
    STATE_CHANGE = "STATE_CHANGE"

class Actor(MongoModel):
    id: str
    name: str
    type: str = "SYSTEM" # SYSTEM, USER, AGENT

class Decision(MongoModel):
    """Record of an AI agent's decision process."""
    made_by: str = Field(..., description="Name of the agent")
    reasoning: str = Field(..., description="Explanation of the decision")
    options_considered: List[str] = []
    chosen_option: str
    confidence: float = Field(1.0, ge=0.0, le=1.0)
    metadata: Dict[str, Any] = {}

class Action(MongoModel):
    """Record of a specific action taken."""
    action_type: ActionType
    performed_by: Actor
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    details: str
    success: bool = True
    metadata: Dict[str, Any] = {}

class AuditEvent(MongoModel):
    """
    Complete audit log entry.
    """
    event_id: str = Field(..., description="Unique event ID")
    invoice_id: Optional[str] = None
    company_id: str
    
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    actor: Actor
    action: Action
    decision: Optional[Decision] = None
    
    related_entities: Dict[str, str] = Field(default_factory=dict, description="e.g. {'po_number': '123'}")
    
    class Config:
        json_schema_extra = {
            "example": {
                "event_id": "evt_123",
                "invoice_id": "inv_456",
                "company_id": "acme",
                "action": {
                    "action_type": "AGENT_DECISION",
                    "details": "Approved invoice based on 3-way match",
                    "success": True
                }
            }
        }
