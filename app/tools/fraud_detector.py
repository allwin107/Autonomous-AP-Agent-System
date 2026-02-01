from typing import Dict, Any, List
from datetime import datetime, timedelta
from app.database import db
from app.models.invoice import InvoiceData
from app.models.vendor import Vendor

class FraudDetector:
    def __init__(self):
        pass

    async def check_bank_details_change(self, vendor_id: str, days: int = 30) -> bool:
        """
        Status: HIGH RISK if bank details changed explicitly within window.
        """
        vendor = await db.vendors.get_by_field("vendor_id", vendor_id)
        if not vendor or not vendor.bank_details:
            return False
            
        if not vendor.bank_details.last_updated:
            return False
            
        diff = datetime.utcnow() - vendor.bank_details.last_updated
        return diff.days < days

    def analyze_fraud_risk(self, invoice_data: InvoiceData, vendor_history: Any = None, 
                          vendor: Any = None, bank_change_detected: bool = False) -> Dict[str, Any]:
        """
        Analyzes the invoice for fraud patterns.
        Returns 'risk_score' (0.0 - 1.0) and 'flags' (List[str]).
        """
        score = 0.0
        flags = []
        
        # 0. Recent Bank Change (Critical)
        if bank_change_detected:
            score += 0.8 # Immediate High Risk
            flags.append("RECENT_BANK_CHANGE")
        
        # Also check if vendor object passed and logic duplicates
        if vendor and vendor.bank_details and vendor.bank_details.last_updated:
            diff = datetime.utcnow() - vendor.bank_details.last_updated
            if diff.days < 30 and "RECENT_BANK_CHANGE" not in flags:
                score += 0.8
                flags.append("RECENT_BANK_CHANGE")
        
        # 1. Rounded Amounts (e.g. 5000.00, 100.00)
        # Often indicates fabricated invoices.
        if invoice_data.total > 0 and invoice_data.total % 100 == 0:
            score += 0.2
            flags.append("ROUNDED_AMOUNT_100")
        elif invoice_data.total > 0 and invoice_data.total % 10 == 0:
            score += 0.1
            flags.append("ROUNDED_AMOUNT_10")
            
        # 2. Weekend Submission
        # Check Created At or Invoice Date? 
        # Let's check Invoice Date for now (though submission timestamp is better if available from metadata)
        if invoice_data.invoice_date.weekday() >= 5: # 5=Saturday, 6=Sunday
            score += 0.1
            flags.append("WEEKEND_DATE")
            
        # 3. High Value (Simple threshold)
        if invoice_data.total > 10000:
            score += 0.1
            flags.append("HIGH_VALUE")
            
        # 4. No Line Items but High Total
        if not invoice_data.line_items and invoice_data.total > 0:
             score += 0.3
             flags.append("NO_LINE_ITEMS")
             
        # Normalize Score
        score = min(score, 1.0)
        
        return {
            "fraud_score": score,
            "flags": flags
        }

fraud_detector = FraudDetector()
