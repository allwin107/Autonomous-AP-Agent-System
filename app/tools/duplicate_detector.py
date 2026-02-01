from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from app.database import db
from app.models.invoice import InvoiceStatus

from difflib import SequenceMatcher

class DuplicateDetector:
    def __init__(self):
        pass

    async def check_duplicates(self, invoice_id: str, vendor_name: str, invoice_number: str, 
                             total: float, invoice_date: datetime, line_items: List[Any] = []) -> Dict[str, Any]:
        """
        Checks for potential duplicates in the database.
        Returns dict with 'is_duplicate', 'match_type', 'conflicting_invoice_id', 'confidence'.
        """
        
        # 1. Exact Match: Vendor + Invoice Number
        existing_exact = await db.invoices.find({
            "data.vendor_name": vendor_name,
            "data.invoice_number": invoice_number,
            "invoice_id": {"$ne": invoice_id}
        })
        
        if existing_exact:
            for inv in existing_exact:
                if inv.status != InvoiceStatus.REJECTED:
                    return {
                        "is_duplicate": True,
                        "match_type": "EXACT_NUMBER",
                        "conflicting_invoice_id": inv.invoice_id,
                        "confidence": 1.0,
                        "details": f"Invoice number {invoice_number} already exists for {vendor_name}"
                    }

        # 2. Fuzzy Match: Vendor + Amount + Date (within 3 days)
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
                    # 3. Line Item Similarity Check (Tie-breaker for fuzzy dates)
                    # If line items are provided, comparing them increases confidence
                    confidence = 0.8 # Base for Date+Amount+Vendor match
                    
                    if line_items and inv.data and inv.data.line_items:
                        # Extract description strings
                        items_a = " ".join([i.description for i in line_items]).lower()
                        items_b = " ".join([i.description for i in inv.data.line_items]).lower()
                        
                        ratio = SequenceMatcher(None, items_a, items_b).ratio()
                        if ratio > 0.8:
                            confidence = 0.95
                            match_type = "FUZZY_PLUS_ITEMS"
                        else:
                            # Amounts match, date close, vendor same, but items differ?
                            # Could be recurring bill (Subscription).
                            # If items differ significantly, maybe NOT a duplicate?
                            # But usually same vendor+amount+close date is suspicious.
                            match_type = "FUZZY_AMOUNT_DATE"
                    else:
                        match_type = "FUZZY_AMOUNT_DATE"

                    return {
                        "is_duplicate": True,
                        "match_type": match_type,
                        "conflicting_invoice_id": inv.invoice_id,
                        "confidence": confidence,
                        "details": f"Similar invoice {inv.invoice_id} found (Score: {confidence})"
                    }

        return {"is_duplicate": False, "confidence": 0.0}

duplicate_detector = DuplicateDetector()
