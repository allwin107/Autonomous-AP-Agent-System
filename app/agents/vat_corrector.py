import logging
from datetime import datetime
from typing import Dict, Any, Optional
from app.models.invoice import Invoice, InvoiceData
from app.tools.vat_validator import vat_validator
from app.tools.vendor_communication import vendor_communication
from app.database import db

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

    async def generate_correction_request(self, invoice: Invoice):
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
        update_data = {
            "validation.vat_valid": False,
            "validation.flags": list(set(invoice.validation.flags + ["VAT_MISMATCH", "CORRECTION_REQUESTED"])),
            "correction_tracking": {
                "request_id": email_id,
                "requested_at": datetime.utcnow(),
                "status": "AWAITING_REPLACEMENT"
            }
        }
        await db.invoices.update(invoice.invoice_id, update_data)
        logger.info(f"Correction request {email_id} sent for invoice {invoice.invoice_id}")

vat_corrector = VATCorrector()
