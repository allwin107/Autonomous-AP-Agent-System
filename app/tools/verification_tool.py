import logging
import uuid
from datetime import datetime
from typing import Optional

from app.database import db
from app.models.verification import VerificationRequest, VerificationStatus, VerificationMethod
from app.tools.notification_tool import notification_tool

logger = logging.getLogger(__name__)

class BankDetailVerification:
    def __init__(self):
        pass

    async def initiate_verification(self, invoice_id: str, vendor_id: str, reason: str) -> VerificationRequest:
        """
        Starts a full verification workflow.
        """
        # Create Request
        req = VerificationRequest(
            invoice_id=invoice_id,
            vendor_id=vendor_id,
            reason=reason,
            risk_level="HIGH"
        )
        await db.db["verification_requests"].insert_one(req.model_dump())
        
        # 1. Trigger Email Confirmation
        await self.request_email_confirmation(req, vendor_id)
        
        # 2. Trigger Callback (Manual task usually)
        await self.request_callback_confirmation(req, vendor_id)
        
        # 3. Require CFO Approval
        await self.require_cfo_approval(req)
        
        return req

    async def request_email_confirmation(self, request: VerificationRequest, vendor_id: str):
        """Sends email to vendor."""
        # Fetch vendor email
        vendor = await db.vendors.get_by_field("vendor_id", vendor_id)
        email = vendor.contact.email if vendor and vendor.contact else "unknown@vendor.com"
        
        await notification_tool.send_notification(
            users=[email],
            subject="URGENT: Verify Bank Details Change",
            message=f"Please define bank details change for invoice {request.invoice_id}. Click here to verify."
        )
        # Update Request status? Usually waits for response. 
        # Here we just mark we requested it.
        # But status stays PENDING until verified.

    async def request_callback_confirmation(self, request: VerificationRequest, vendor_id: str):
        """Logs need for callback."""
        logger.info(f"Callback required for Vendor {vendor_id} regarding Invoice {request.invoice_id}")
        # Could create a task in a task management system
        
    async def require_cfo_approval(self, request: VerificationRequest):
        """Flags for CFO."""
        # Fetch CFO email?
        cfo_email = "cfo@company.com" # Config
        await notification_tool.send_notification(
            users=[cfo_email],
            subject=f"FRAUD ALERT: Bank Change Approval Required {request.invoice_id}",
            message=f"High risk invoice needs approval. Reason: {request.reason}"
        )
        
        await self._update_status(request.invoice_id, "cfo_approval_status", VerificationStatus.CFO_APPROVAL_NEEDED)

    async def verify_step(self, invoice_id: str, step: str, approver: str, notes: str) -> bool:
        """
        Updates a specific verification step (email, callback, cfo).
        step: 'email', 'callback', 'cfo'
        """
        field_map = {
            "email": "email_verification_status",
            "callback": "callback_verification_status",
            "cfo": "cfo_approval_status"
        }
        
        if step not in field_map:
            return False
            
        update_field = field_map[step]
        
        # Find request
        req_doc = await db.db["verification_requests"].find_one({"invoice_id": invoice_id})
        if not req_doc:
            return False
            
        await db.db["verification_requests"].update_one(
            {"invoice_id": invoice_id},
            {"$set": {
                update_field: VerificationStatus.VERIFIED,
                "updated_at": datetime.utcnow()
            },
            "$push": {"notes": f"{step.upper()} Verified by {approver}: {notes}"}}
        )
        
        # Check if all verified
        updated_doc = await db.db["verification_requests"].find_one({"invoice_id": invoice_id})
        req = VerificationRequest(**updated_doc)
        
        if req.is_fully_verified():
             await db.db["verification_requests"].update_one(
                {"invoice_id": invoice_id},
                {"$set": {"overall_status": VerificationStatus.VERIFIED}}
            )
             logger.info(f"Invoice {invoice_id} is FULLY VERIFIED.")
             
             # Unblock Invoice?
             # That requires logic in ValidationAgent or calling it here.
             # Ideally ValidationAgent checks this status periodically or receives event.
             # For now, we assume Audit/Validation Agent checks this.
             
        return True

    async def _update_status(self, invoice_id: str, field: str, status: str):
        await db.db["verification_requests"].update_one(
            {"invoice_id": invoice_id},
            {"$set": {field: status, "updated_at": datetime.utcnow()}}
        )

verification_tool = BankDetailVerification()
