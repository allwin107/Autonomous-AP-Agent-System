from datetime import datetime
from typing import List, Dict, Any
from pydantic import Field
from app.models.base import MongoModel

class MemoryItem(MongoModel):
    company_id: str
    memory_type: str # POLICY, PAST_DECISION, CORRECTION
    
    content: str
    embedding: List[float] # 384 dim vector
    
    metadata: Dict[str, Any] = {}
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
