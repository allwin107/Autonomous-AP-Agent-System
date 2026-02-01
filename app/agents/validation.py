import logging
from typing import Dict, Any, List

from app.database import db
from app.models.invoice import InvoiceStatus, InvoiceData, ValidationResults
from app.models.vendor import VerificationStatus
from app.tools.vat_validator import vat_validator
from app.tools.duplicate_detector import duplicate_detector
from app.tools.fraud_detector import fraud_detector

logger = logging.getLogger(__name__)

class ValidationAgent:
    def __init__(self):
        pass

    async def validation_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validates the extracted invoice data.
        """
        invoice_id = state.get("invoice_id")
        if not invoice_id:
            logger.error("No invoice_id in state")
            state["errors"] = ["Missing invoice_id"]
            return state

        try:
            # 1. Fetch Invoice
            invoice = await db.invoices.get_by_field("invoice_id", invoice_id)
            if not invoice or not invoice.data:
                logger.error(f"Invoice {invoice_id} not found or missing data")
                state["errors"] = ["Invoice data missing"]
                return state
            
            # Using Pydantic model for easier access
            data: InvoiceData = InvoiceData(**invoice.data.model_dump())
            
            # 2. Duplicate Detection
            dup_result = await duplicate_detector.check_duplicates(
                invoice_id, data.vendor_name, data.invoice_number, data.total, data.invoice_date
            )
            
            # 3. VAT Validation
            vat_result = vat_validator.validate_vat(data)
            
            # 4. Vendor Validation
            # Try to lookup vendor by name if ID not present
            vendor_approved = False
            vendor = None
            if data.vendor_id:
                vendor = await db.vendors.get_by_field("vendor_id", data.vendor_id)
            elif data.vendor_name:
                vendor = await db.vendors.get_by_field("name", data.vendor_name)

            if vendor and vendor.verification_status == VerificationStatus.VERIFIED:
                vendor_approved = True
                # Link vendor ID if not already linked
                if not data.vendor_id:
                    data.vendor_id = vendor.vendor_id
                    await db.invoices.update(invoice_id, {"data.vendor_id": vendor.vendor_id})
            
            # 5. Fraud Analysis
            fraud_result = fraud_detector.analyze_fraud_risk(data)
            
            # 6. Aggregate Results
            flags = fraud_result["flags"]
            if not vat_result["valid"]:
                flags.append(f"VAT_MISMATCH: {vat_result['details']}")
            if not vendor_approved:
                flags.append("VENDOR_NOT_APPROVED")
            if dup_result["is_duplicate"]:
                flags.append(f"POTENTIAL_DUPLICATE: {dup_result['match_type']}")
            
            validation_results = ValidationResults(
                is_duplicate=dup_result["is_duplicate"],
                vat_valid=vat_result["valid"],
                vendor_approved=vendor_approved,
                fraud_score=fraud_result["fraud_score"],
                flags=flags
            )
            
            # 7. Determine Next State
            next_state = InvoiceStatus.MATCHING # Default path
            
            # Logic to block or flag
            if dup_result["is_duplicate"]:
                next_state = InvoiceStatus.EXCEPTION # Needs manual review
            elif fraud_result["fraud_score"] > 0.7:
                 next_state = InvoiceStatus.EXCEPTION
            elif not vat_result["valid"] and data.vat_amount > 0:
                 # Strict on VAT? Maybe just flag but proceed to matching if amount is small?
                 # Let's be safe and EXCEPTION
                 next_state = InvoiceStatus.EXCEPTION
            elif not vendor_approved:
                 # If vendor unknown, might need to create it or review
                 next_state = InvoiceStatus.AWAITING_APPROVAL # Or some onboarding state
            
            # Update DB
            await db.invoices.update(invoice_id, {
                "status": next_state,
                "validation": validation_results.model_dump()
            })
            
            # Update State
            state["validation_results"] = validation_results.model_dump()
            state["current_state"] = next_state
            state["risk_score"] = fraud_result["fraud_score"]
            
            logger.info(f"Validation complete for {invoice_id}. Next State: {next_state}")

        except Exception as e:
            logger.error(f"Validation failed: {e}")
            state["errors"] = [str(e)]
            await db.invoices.update(invoice_id, {"status": InvoiceStatus.EXCEPTION})
            
        return state

validation_agent = ValidationAgent()
