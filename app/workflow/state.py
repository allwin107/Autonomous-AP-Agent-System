from typing import TypedDict, List, Dict, Any, Optional, Annotated
import operator

class InvoiceState(TypedDict):
    """
    Represents the flow state of an invoice through the processing pipeline.
    """
    # Core Identity
    invoice_id: str
    company_id: str
    
    # Workflow Control
    current_state: str # Matches InvoiceStatus enum
    previous_state: Optional[str]
    
    # Data Data
    invoice_data: Optional[Dict[str, Any]] # Serialized InvoiceData
    
    # Validation & Logic Results
    validation_results: Optional[Dict[str, Any]] # Serialized ValidationResults
    matching_results: Optional[Dict[str, Any]] # Serialized MatchingResults
    payment_proposal: Optional[Dict[str, Any]]
    
    # Risk & Flags
    risk_score: float
    human_approval_required: bool
    
    # Error Handling
    errors: Annotated[List[str], operator.add] # Append errors instead of overwriting
    retry_count: int
