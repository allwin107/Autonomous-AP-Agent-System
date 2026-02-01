import sys
import os
sys.path.append(os.getcwd())
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from app.agents.validation import ValidationAgent
from app.agents.vat_corrector import vat_corrector
from app.models.invoice import InvoiceStatus, InvoiceData, Invoice, ValidationResults
from app.models.vendor import Vendor, VendorContact

@pytest.mark.asyncio
async def test_vat_discrepancy_triggers_corrector():
    # Setup: Invoice with clear VAT discrepancy (Subtotal 100, VAT 10, should be 20)
    data = InvoiceData(
        vendor_id="v1", vendor_name="Vendor A", invoice_number="INV-VAT-01",
        invoice_date=datetime.utcnow(), subtotal=100.0, vat_amount=10.0, total=110.0,
        currency="GBP"
    )
    
    invoice = Invoice(
        invoice_id="inv_test", company_id="c1", status=InvoiceStatus.VALIDATION,
        data=data, validation=ValidationResults(flags=[])
    )
    
    vendor = Vendor(
        vendor_id="v1", company_id="c1", name="Vendor A",
        approval_status="APPROVED",
        contact=VendorContact(email="vendor@example.com")
    )
    
    with patch("app.agents.validation.db") as mock_db, \
         patch("app.agents.validation.duplicate_detector") as mock_dup, \
         patch("app.agents.validation.fraud_detector") as mock_fraud, \
         patch("app.agents.vat_corrector.db") as mock_corr_db, \
         patch("app.tools.vendor_communication.notification_tool") as mock_notif, \
         patch("app.tools.vat_validator.vat_validator.validate_vat") as mock_vat_val:
         
        # Mock DB
        mock_db.invoices.get_by_field = AsyncMock(return_value=invoice)
        mock_db.vendors.get_by_field = AsyncMock(return_value=vendor)
        mock_db.invoices.update = AsyncMock()
        
        mock_corr_db.vendors.get_by_field = AsyncMock(return_value=vendor)
        mock_corr_db.invoices.update = AsyncMock()
        
        # Mock validators
        mock_dup.check_duplicates = AsyncMock(return_value={"is_duplicate": False})
        mock_fraud.analyze_fraud_risk = MagicMock(return_value={"fraud_score": 0.1, "flags": []})
        mock_fraud.check_bank_details_change = AsyncMock(return_value=False)
        
        # VAT Validator should return invalid
        mock_vat_val.return_value = {
            "valid": False,
            "details": "VAT amount 10.0 does not match 20% (20.00)"
        }
        
        # Mock Notification send
        mock_notif.send_notification = AsyncMock()
        
        agent = ValidationAgent()
        state = {"invoice_id": "inv_test"}
        
        result = await agent.validation_node(state)
        
        # Assertions
        assert result["current_state"] == InvoiceStatus.AWAITING_CORRECTION
        
        # Check if correction request was triggered (via notification)
        mock_notif.send_notification.assert_called()
        
        # Check if invoice was updated with flags
        args, kwargs = mock_db.invoices.update.call_args
        actual_flags = args[1]["validation"]["flags"]
        assert any("VAT_MISMATCH" in flag for flag in actual_flags)
        
        # Check corrector's self track (if we had a way to access it, but we use DB)
        # Verify the body contains the calculation
        notif_args = mock_notif.send_notification.call_args
        # users=[email], ...
        body = notif_args.kwargs["message"]
        assert "Expected VAT: £20.00" in body
        assert "Current VAT: £10.00" in body
        assert "Expected VAT is calculated as 20% of the subtotal (£100.00)" in body

@pytest.mark.asyncio
async def test_detect_vat_error_logic():
    # Unit test for vat_corrector.detect_vat_error
    # 200 * 0.20 = 40. 15.0 is neither 20% nor 5% (10.0)
    data = InvoiceData(
        vendor_id="v1", vendor_name="V", invoice_number="N",
        invoice_date=datetime.utcnow(), subtotal=200.0, vat_amount=15.0, total=215.0
    )
    invoice = Invoice(invoice_id="i", company_id="c", data=data)
    
    error = await vat_corrector.detect_vat_error(invoice)
    assert error is not None
    assert error["expected_vat"] == 40.0
    assert error["current_vat"] == 15.0
