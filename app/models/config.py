from typing import List, Optional, Dict, Any
from pydantic import Field
from app.models.base import MongoModel

class ApprovalRule(MongoModel):
    amount_min: float
    amount_max: Optional[float] = None
    approvers: List[str]

class ValidationRules(MongoModel):
    max_invoice_amount: float = 50000.0
    vat_tolerance: float = 0.05
    duplicate_detection_window_days: int = 90
    approved_vendors_only: bool = True

class CompanyConfig(MongoModel):
    company_id: str
    company_name: str
    
    currency: str = "GBP"
    
    validation_rules: ValidationRules = ValidationRules()
    
    approval_matrix: List[ApprovalRule] = []
    
    matching_tolerances: Dict[str, float] = {
        "quantity_variance_percent": 5.0,
        "price_variance_percent": 2.0
    }
