import sys
import os
sys.path.append(os.getcwd())
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from app.agents.validation import ValidationAgent
from app.tools.fraud_detector import FraudDetector, fraud_detector
from app.tools.verification_tool import BankDetailVerification, verification_tool
from app.models.invoice import InvoiceStatus, InvoiceData
from app.models.vendor import Vendor, BankDetails, VerificationStatus

@pytest.mark.asyncio
async def test_bank_detail_change_detection():
    # Setup Vendor with recent bank change
    vendor = Vendor(
        vendor_id="v1", company_id="c1", name="Risky Vendor",
        bank_details=BankDetails(
            account_name="New Account", account_number="123",
            last_updated=datetime.utcnow() - timedelta(days=2) # Changed 2 days ago
        )
    )
    
    with patch("app.tools.fraud_detector.db") as mock_db:
        mock_db.vendors.get_by_field = AsyncMock(return_value=vendor)
        
        detector = FraudDetector()
        is_change = await detector.check_bank_details_change("v1", days=30)
        
        assert is_change is True

@pytest.mark.asyncio
async def test_validation_triggers_verification():
    # Test complete flow
    with patch("app.agents.validation.db") as mock_db, \
         patch("app.agents.validation.duplicate_detector") as mock_dup, \
         patch("app.agents.validation.vat_validator.validate_vat", return_value={"valid": True}), \
         patch("app.tools.verification_tool.db") as mock_ver_db, \
         patch.object(verification_tool, "initiate_verification", new_callable=AsyncMock) as mock_init_ver, \
         patch.object(fraud_detector, "check_bank_details_change", new_callable=AsyncMock) as mock_check_bank:
         
        mock_check_bank.return_value = True # Simulate Bank Change Detected
        
        # Vendor setup
        vendor = Vendor(
            vendor_id="v1", company_id="c1", name="Risky Vendor",
            approval_status="APPROVED",
             bank_details=BankDetails(
                account_name="New Account", account_number="123",
                last_updated=datetime.utcnow()
            )
        )
        
        # Invoice setup
        invoice_data = InvoiceData(
            vendor_id="v1", vendor_name="Risky Vendor", invoice_number="INV1",
            invoice_date=datetime.now(), total=5000.0, currency="USD",
            line_items=[]
        )
        mock_invoice = MagicMock()
        mock_invoice.data = invoice_data
        
        # Mock DB returns
        mock_db.invoices.get_by_field = AsyncMock(return_value=mock_invoice)
        mock_db.vendors.get_by_field = AsyncMock(return_value=vendor) 
        mock_db.invoices.update = AsyncMock()
        mock_dup.check_duplicates = AsyncMock(return_value={"is_duplicate": False})
        
        # Mock Verification DB insert
        mock_ver_db.db.__getitem__.return_value.insert_one = AsyncMock()
        mock_ver_db.vendors.get_by_field = AsyncMock(return_value=vendor) # For verify tool email
        
        agent = ValidationAgent()
        state = {"invoice_id": "inv1"}
        
        result = await agent.validation_node(state)
        
        # Assertions
        mock_check_bank.assert_called_with("v1")
        mock_init_ver.assert_called()
        
        assert "RECENT_BANK_CHANGE" in result["validation_results"]["flags"]
        assert result["current_state"] == InvoiceStatus.EXCEPTION

@pytest.mark.asyncio
async def test_verification_tool_steps():
    tool = BankDetailVerification()
    
    with patch("app.tools.verification_tool.db") as mock_db, \
         patch("app.tools.verification_tool.notification_tool") as mock_notif:
        
        mock_notif.send_notification = AsyncMock()
        mock_db.db.__getitem__.return_value.insert_one = AsyncMock()
        mock_db.db.__getitem__.return_value.update_one = AsyncMock()
        mock_db.db.__getitem__.return_value.find_one = AsyncMock(return_value={
            "invoice_id": "inv1", "vendor_id": "v1", "risk_level": "HIGH", "reason": "TEST",
            "email_verification_status": "PENDING", "callback_verification_status": "PENDING",
            "cfo_approval_status": "PENDING", "overall_status": "PENDING", "notes": []
        })
        mock_db.vendors.get_by_field = AsyncMock(return_value=MagicMock(contact=MagicMock(email="test@vendor.com")))
        
        await tool.initiate_verification("inv1", "v1", "TEST")
        
        # Check Notifications (Email + CFO)
        assert mock_notif.send_notification.call_count == 2 
        # 1 for vendor, 1 for CFO
