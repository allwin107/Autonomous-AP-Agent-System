from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from app.database import db
from app.models.invoice import InvoiceStatus

class DuplicateDetector:
    def __init__(self):
        pass

    async def check_duplicates(self, invoice_id: str, vendor_name: str, invoice_number: str, 
                             total: float, invoice_date: datetime) -> Dict[str, Any]:
        """
        Checks for potential duplicates in the database.
        Returns dict with 'is_duplicate', 'match_type', 'conflicting_invoice_id'.
        """
        
        # 1. Exact Match: Vendor + Invoice Number
        # Exclude current invoice itself
        existing_exact = await db.invoices.find({
            "data.vendor_name": vendor_name,
            "data.invoice_number": invoice_number,
            "invoice_id": {"$ne": invoice_id}
        })
        
        if existing_exact:
            # Check validity of other invoice (ignore REJECTED?)
            for inv in existing_exact:
                if inv.status != InvoiceStatus.REJECTED:
                    return {
                        "is_duplicate": True,
                        "match_type": "EXACT_NUMBER",
                        "conflicting_invoice_id": inv.invoice_id,
                        "details": f"Invoice number {invoice_number} already exists for {vendor_name}"
                    }

        # 2. Fuzzy Match: Vendor + Amount + Date (within 3 days)
        # This catches "INV-001" vs "INV001" typos or re-submissions without number
        date_start = invoice_date - timedelta(days=3)
        date_end = invoice_date + timedelta(days=3)
        
        existing_fuzzy = await db.invoices.find({
            "data.vendor_name": vendor_name,
            "data.total": total,
            "data.invoice_date": {"$gte": date_start, "$lte": date_end},
            "invoice_id": {"$ne": invoice_id}
        })

        if existing_fuzzy:
             for inv in existing_fuzzy:
                if inv.status != InvoiceStatus.REJECTED:
                    return {
                        "is_duplicate": True,
                        "match_type": "FUZZY_AMOUNT_DATE",
                        "conflicting_invoice_id": inv.invoice_id,
                        "details": f"Similar invoice found: {inv.invoice_id} with same vendor, amount, and close date"
                    }

        return {"is_duplicate": False}

duplicate_detector = DuplicateDetector()
