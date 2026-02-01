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

    def generate_vat_explanation(self, subtotal: float, rate: float = 0.20) -> str:
        """
        Generates a text explanation of the VAT calculation.
        """
        return f"Expected VAT is calculated as {rate*100:.0f}% of the subtotal (£{subtotal:,.2f})."

    def generate_correction_request_email(self, vendor_name: str, invoice_number: str, subtotal: float, current_vat: float, expected_vat: float) -> str:
        """
        Generates the formatted string for a VAT correction request.
        """
        difference = expected_vat - current_vat
        explanation = self.generate_vat_explanation(subtotal)
        
        template = f"""
Subject: VAT Correction Required - Invoice {invoice_number}

Dear {vendor_name},

We've identified a VAT calculation error on invoice {invoice_number}.

Current VAT: £{current_vat:,.2f}
Expected VAT: £{expected_vat:,.2f}
Difference: £{difference:,.2f}

Please send a corrected invoice with the proper VAT calculation.

Calculation Details:
{explanation}

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
