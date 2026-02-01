from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import Field
from app.models.base import MongoModel
from datetime import datetime

class MemoryType(str, Enum):
    REFLECTION = "REFLECTION"
    PATTERN = "PATTERN"
    ERROR = "ERROR"
    OPTIMIZATION = "OPTIMIZATION"

class Memory(MongoModel):
    """
    Semantic memory entry for vector-based learning.
    """
    type: MemoryType = MemoryType.REFLECTION
    observation: str = Field(..., description="What was observed (the scenario)")
    learning: str = Field(..., description="The insight or rule derived")
    pattern: Optional[str] = Field(None, description="Identified pattern name")
    
    vendor_name: Optional[str] = None
    vendor_id: Optional[str] = None
    
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    
    # Vector embedding - list of floats (384 dimensions for all-MiniLM-L6-v2)
    embedding: Optional[List[float]] = None
    
    metadata: Dict[str, Any] = {}
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
