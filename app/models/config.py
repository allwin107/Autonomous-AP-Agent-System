from typing import List, Dict, Optional
from pydantic import Field, field_validator
from app.models.base import MongoModel

class ValidationRules(MongoModel):
    max_invoice_amount: float = Field(50000.0, description="Max amount before special approval")
    vat_tolerance: float = Field(0.05, description="Allowed VAT calculation variance")
    duplicate_detection_window_days: int = 90
    approved_vendors_only: bool = True
    require_po_above: float = 0.0

class MatchingTolerances(MongoModel):
    quantity_variance_percent: float = 5.0
    price_variance_percent: float = 2.0
    total_amount_variance: float = 1.0

class ApprovalRule(MongoModel):
    """Rule defining who needs to approve what."""
    rule_id: str
    amount_min: float
    amount_max: Optional[float] = None
    required_role: Optional[str] = None
    specific_approvers: List[str] = []

    @field_validator('amount_max')
    @classmethod
    def validate_max(cls, v, info):
        if v is not None and 'amount_min' in info.data and v < info.data['amount_min']:
            raise ValueError('amount_max must be greater than amount_min')
        return v

class ApprovalMatrix(MongoModel):
    rules: List[ApprovalRule] = []

class GLMapping(MongoModel):
    """Mapping of categories to GL Codes."""
    default_expense_gl: str = "7400" # Office Supplies / Misc
    vat_recoverable_gl: str = "1510"
    accounts_payable_gl: str = "2100"
    
    # Category overrides, e.g. {"Rent": "7200", "Salaries": "7100"}
    category_map: Dict[str, str] = {
        "Office Supplies": "7400",
        "Salaries": "7100",
        "Rent": "7200",
        "Hardware": "7400",
        "Software": "7400"
    }

class SLASettings(MongoModel):
    default_approval_sla_hours: int = 48
    payment_warning_days: int = 7
    payment_urgent_days: int = 3
    payment_critical_hours: int = 24

class CompanyConfig(MongoModel):
    """
    Multi-tenant configuration document.
    """
    company_id: str = Field(..., description="Unique Tenant ID")
    company_name: str
    
    base_currency: str = "GBP"
    
    validation_rules: ValidationRules = Field(default_factory=ValidationRules)
    matching_tolerances: MatchingTolerances = Field(default_factory=MatchingTolerances)
    approval_matrix: ApprovalMatrix = Field(default_factory=ApprovalMatrix)
    gl_mapping: GLMapping = Field(default_factory=GLMapping)
    sla_settings: SLASettings = Field(default_factory=SLASettings)
    
    system_enabled: bool = True
    notification_email: Optional[str] = None
