from datetime import datetime
from typing import List, Optional
from enum import Enum
from pydantic import Field
from app.models.base import MongoModel

class EntryType(str, Enum):
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"

class JournalLine(MongoModel):
    gl_code: str
    account_name: str
    description: str
    type: EntryType
    amount: float
    department: Optional[str] = None

class JournalEntry(MongoModel):
    """Double-entry bookkeeping record."""
    entry_id: str
    date: datetime
    posting_date: datetime
    reference: str
    source_document: str # Invoice ID
    currency: str
    
    lines: List[JournalLine]
    
    total_debit: float
    total_credit: float
    
    status: str = "DRAFT" # DRAFT, POSTED, ERROR
    
    def validate_balance(self) -> bool:
        return abs(self.total_debit - self.total_credit) < 0.01

class LedgerBalance(MongoModel):
    """Balance for a GL Account."""
    gl_code: str
    balance: float
    updated_at: datetime = Field(default_factory=datetime.utcnow)
