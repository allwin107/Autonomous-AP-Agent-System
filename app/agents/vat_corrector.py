import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from app.models.invoice import Invoice, InvoiceData
from app.tools.vat_validator import vat_validator
from app.tools.vendor_communication import vendor_communication
from app.database import db
from app.memory.semantic_memory import semantic_memory
from app.models.memory import Memory, MemoryType

logger = logging.getLogger(__name__)

class VATCorrector:
    """
    Agent responsible for detecting VAT errors and coordinating corrections with vendors.
    """
    
    def calculate_correct_vat(self, invoice_data: InvoiceData) -> float:
        """
        Calculates the expected VAT based on standard UK rate (20%).
        """
        # Note: In a production system, this would look up the specific rate applied 
        # or use the line-item level tax codes if available.
        return round(invoice_data.subtotal * 0.20, 2)

    async def detect_vat_error(self, invoice: Invoice) -> Optional[Dict[str, Any]]:
        """
        Detects if there is a VAT mismatch and returns error details.
        """
        if not invoice.data:
            return None
            
        res = vat_validator.validate_vat(invoice.data)
        if not res["valid"]:
            expected = self.calculate_correct_vat(invoice.data)
            return {
                "current_vat": invoice.data.vat_amount,
                "expected_vat": expected,
                "subtotal": invoice.data.subtotal,
                "error_details": res["details"]
            }
        return None

    async def generate_correction_request(self, invoice: Invoice, timeout_days: int = 7):
        """
        Generates and tracks a correction request for a flawed VAT invoice.
        """
        error = await self.detect_vat_error(invoice)
        if not error:
            logger.info(f"No VAT error detected for invoice {invoice.invoice_id}")
            return

        # Fetch vendor details for email
        vendor = await db.vendors.get_by_field("vendor_id", invoice.data.vendor_id)
        if not vendor or not vendor.contact or not vendor.contact.email:
            logger.error(f"Cannot send correction request for invoice {invoice.invoice_id}: Vendor contact missing.")
            return

        email_body = vendor_communication.generate_correction_request_email(
            vendor_name=vendor.name,
            invoice_number=invoice.data.invoice_number,
            subtotal=error["subtotal"],
            current_vat=error["current_vat"],
            expected_vat=error["expected_vat"]
        )
        
        email_id = await vendor_communication.send_email(
            vendor_email=vendor.contact.email,
            subject=f"VAT Correction Required - {invoice.data.invoice_number}",
            body=email_body
        )
        
        # Track status in invoice metadata
        due_date = datetime.utcnow() + timedelta(days=timeout_days)
        update_data = {
            "status": "AWAITING_CORRECTION",
            "validation.vat_valid": False,
            "validation.flags": list(set(invoice.validation.flags + ["VAT_MISMATCH", "CORRECTION_REQUESTED"])),
            "correction_tracking": {
                "request_id": email_id,
                "requested_at": datetime.utcnow(),
                "due_date": due_date,
                "status": "AWAITING_REPLACEMENT",
                "overridden": False
            }
        }
        await db.invoices.update(invoice.invoice_id, update_data)
        logger.info(f"Correction request {email_id} sent for invoice {invoice.invoice_id}. Due: {due_date}")

        # Store learning in Semantic Memory
        try:
            memory = Memory(
                type=MemoryType.ERROR,
                observation=f"VAT discrepancy on invoice {invoice.data.invoice_number} from {vendor.name}",
                learning=f"Vendor {vendor.name} calculated VAT as £{error['current_vat']} instead of £{error['expected_vat']}. Standardize to 20%.",
                vendor_name=vendor.name,
                vendor_id=vendor.vendor_id,
                confidence=1.0
            )
            await semantic_memory.store_learning(memory)
        except Exception as e:
            logger.warning(f"Failed to store learning in semantic memory: {e}")

    async def handle_timeout(self, invoice_id: str):
        """
        Fires if vendor hasn't responded by due_date. 
        In practice, would be called by a cron/scheduled task.
        """
        invoice = await db.invoices.get_by_field("invoice_id", invoice_id)
        if not invoice or invoice.status != "AWAITING_CORRECTION":
            return
            
        tracking = getattr(invoice, "correction_tracking", {})
        if not tracking or tracking.get("overridden"):
            return
            
        if datetime.utcnow() > tracking.get("due_date", datetime.utcnow()):
             logger.warning(f"VAT Correction timeout for {invoice_id}. Escalating.")
             await db.invoices.update(invoice_id, {
                 "status": "EXCEPTION",
                 "correction_tracking.status": "TIMEOUT_ESCALATED"
             })

    async def manual_override(self, invoice_id: str, reason: str, approver: str):
        """
        Allows a user to override the VAT error and proceed to matching.
        """
        await db.invoices.update(invoice_id, {
            "status": "MATCHING",
            "validation.vat_valid": True, # Force valid
            "correction_tracking.overridden": True,
            "correction_tracking.override_reason": reason,
            "correction_tracking.overridden_by": approver,
            "correction_tracking.overridden_at": datetime.utcnow()
        })
        logger.info(f"VAT Correction overridden for {invoice_id} by {approver}")

vat_corrector = VATCorrector()
