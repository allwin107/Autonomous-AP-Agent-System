import logging
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime
from app.tools.notification_tool import notification_tool

logger = logging.getLogger(__name__)

class VendorCommunication:
    """
    Handles all outbound communication with vendors regarding their invoices.
    """
    def __init__(self):
        self.sent_emails = {} # In-memory track for demonstration

    async def send_email(self, vendor_email: str, subject: str, body: str, attachments: List[str] = []) -> str:
        """
        Sends an email to a vendor.
        Returns a unique email_id.
        """
        email_id = str(uuid.uuid4())
        
        # Use existing notification tool for delivery logic
        await notification_tool.send_notification(
            users=[vendor_email],
            subject=subject,
            message=body,
            channels=["email"]
        )
        
        self.sent_emails[email_id] = {
            "vendor_email": vendor_email,
            "subject": subject,
            "timestamp": datetime.utcnow(),
            "status": "SENT"
        }
        
        logger.info(f"Email {email_id} sent to {vendor_email}: {subject}")
        return email_id

    def generate_correction_request_email(self, invoice_number: str, subtotal: float, current_vat: float, expected_vat: float) -> str:
        """
        Generates the formatted string for a VAT correction request.
        """
        diff = expected_vat - current_vat
        
        template = f"""
Subject: Correction Required: VAT Mismatch on Invoice {invoice_number}

Dear Vendor,

We are writing regarding invoice {invoice_number} submitted to our system.

Our automated validation has detected a discrepancy in the VAT calculation:
- Invoice Subtotal: {subtotal:.2f}
- VAT Amount on Invoice: {current_vat:.2f}
- Expected VAT (20%): {expected_vat:.2f}
- Discrepancy: {diff:.2f}

Please provide a corrected invoice with the accurate VAT calculations to ensure timely processing and payment. 

If you believe this calculation is correct (e.g., mixed VAT rates apply), please provide a detailed breakdown of the tax rates used.

Until a correction is received or clarified, this invoice cannot proceed to payment.

Regards,
Accounts Payable Department
Autonomous AP System
"""
        return template.strip()

    async def track_email_status(self, email_id: str) -> Dict[str, Any]:
        """
        Returns the status of a previously sent email.
        """
        return self.sent_emails.get(email_id, {"status": "NOT_FOUND"})

vendor_communication = VendorCommunication()
