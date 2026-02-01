from typing import Dict, Any, List
from datetime import datetime
from app.models.invoice import InvoiceData

class FraudDetector:
    def __init__(self):
        pass

    def analyze_fraud_risk(self, invoice_data: InvoiceData, vendor_history: Any = None) -> Dict[str, Any]:
        """
        Analyzes the invoice for fraud patterns.
        Returns 'risk_score' (0.0 - 1.0) and 'flags' (List[str]).
        """
        score = 0.0
        flags = []
        
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
