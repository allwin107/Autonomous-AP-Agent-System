from typing import List, Dict, Any, Optional
from app.models.invoice import InvoiceData

class VATValidator:
    def __init__(self):
        # UK VAT Rates
        self.STANDARD_RATE = 0.20
        self.REDUCED_RATE = 0.05
        self.ZERO_RATE = 0.0
        self.TOLERANCE = 0.05 # 5p tolerance

    def validate_vat(self, invoice_data: InvoiceData) -> Dict[str, Any]:
        """
        Validates VAT calculations on the invoice.
        Returns a dict with 'valid' (bool) and 'details' (str).
        """
        # If explicit VAT amount is missing, we can't fully validate, 
        # but we can check if it aligns with standard rate if provided.
        
        calculated_vat = 0.0
        
        # Method 1: Line item aggregation (most accurate)
        # But our LineItem doesn't enforce a VAT Code per line yet, 
        # so we'll infer based on 'taxable' assumption or just check global totals first.
        
        # Method 2: Global Check
        # Check if declared VAT matches 20% of Subtotal
        expected_vat_standard = invoice_data.subtotal * self.STANDARD_RATE
        diff_standard = abs(invoice_data.vat_amount - expected_vat_standard)
        
        if diff_standard <= self.TOLERANCE:
            return {"valid": True, "details": "Matches Standard Rate (20%)"}
            
        # Check Reduced Rate
        expected_vat_reduced = invoice_data.subtotal * self.REDUCED_RATE
        diff_reduced = abs(invoice_data.vat_amount - expected_vat_reduced)
        
        if diff_reduced <= self.TOLERANCE:
            return {"valid": True, "details": "Matches Reduced Rate (5%)"}

        # Check Zero Rate / Exempt
        if invoice_data.vat_amount == 0.0:
            return {"valid": True, "details": "Zero Rated / Exempt"}
            
        # Check if multiple mixed rates? (Complex without line item tax codes)
        # For now, mark invalid if no single rate matches simple total logic
        
        percentage = (invoice_data.vat_amount / invoice_data.subtotal) * 100 if invoice_data.subtotal > 0 else 0
        
        return {
            "valid": False, 
            "details": f"VAT amount {invoice_data.vat_amount} does not match 20% ({expected_vat_standard:.2f}) or 5%. Implied rate: {percentage:.1f}%"
        }

vat_validator = VATValidator()
