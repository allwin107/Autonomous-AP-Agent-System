import sys
import os
sys.path.append(os.getcwd())
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from app.agents.validation import ValidationAgent
from app.models.invoice import Invoice, InvoiceStatus, InvoiceData, ValidationResults
from app.models.vendor import Vendor, VerificationStatus

@pytest.mark.asyncio
async def test_validation_node_success():
    with patch("app.agents.validation.db") as mock_db:
        # Mock Invoice
        mock_invoice = MagicMock()
        mock_invoice.invoice_id = "inv_valid"
        mock_invoice.company_id = "acme"
        mock_invoice.status = InvoiceStatus.EXTRACTION
        
        # Valid data
        data = InvoiceData(
            vendor_name="Test Vendor",
            invoice_number="INV-100",
            invoice_date=datetime.now(),
            total=120.0,
            subtotal=100.0,
            vat_amount=20.0, # 20%
            line_items=[]
        )
        mock_invoice.data = data
        mock_db.invoices.get_by_field = AsyncMock(return_value=mock_invoice)
        mock_db.invoices.update = AsyncMock()
        
        # Mock Vendor (Verified)
        mock_vendor = MagicMock(spec=Vendor)
        mock_vendor.vendor_id = "ven_1"
        mock_vendor.verification_status = VerificationStatus.VERIFIED
        mock_db.vendors.get_by_field = AsyncMock(return_value=mock_vendor)
        
        # Mock Tools
        with patch("app.agents.validation.duplicate_detector") as mock_dup:
            mock_dup.check_duplicates = AsyncMock(return_value={"is_duplicate": False})
            
            with patch("app.agents.validation.vat_validator") as mock_vat:
                mock_vat.validate_vat.return_value = {"valid": True, "details": "OK"}
                
                with patch("app.agents.validation.fraud_detector") as mock_fraud:
                    mock_fraud.analyze_fraud_risk.return_value = {"fraud_score": 0.0, "flags": []}
                    
                    agent = ValidationAgent()
                    state = {"invoice_id": "inv_valid"}
                    result = await agent.validation_node(state)
                    
                    # Verify
                    assert result["current_state"] == InvoiceStatus.MATCHING
                    assert result["validation_results"]["vat_valid"] is True
                    assert result["validation_results"]["vendor_approved"] is True

@pytest.mark.asyncio
async def test_validation_node_duplicate():
    with patch("app.agents.validation.db") as mock_db:
        mock_invoice = MagicMock()
        mock_invoice.invoice_id = "inv_dup"
        # ... setup data ...
        data = InvoiceData(vendor_name="Bad Vendor", invoice_number="DUP", invoice_date=datetime.now(), total=100.0)
        mock_invoice.data = data
        mock_db.invoices.get_by_field = AsyncMock(return_value=mock_invoice)
        mock_db.vendors.get_by_field = AsyncMock(return_value=None)
        mock_db.invoices.update = AsyncMock()

        with patch("app.agents.validation.duplicate_detector") as mock_dup:
            mock_dup.check_duplicates = AsyncMock(return_value={"is_duplicate": True, "match_type": "EXACT"})
            
            with patch("app.agents.validation.vat_validator") as mock_vat:
                 mock_vat.validate_vat.return_value = {"valid": True}
                 with patch("app.agents.validation.fraud_detector") as mock_fraud:
                      mock_fraud.analyze_fraud_risk.return_value = {"fraud_score": 0.0, "flags": []}
                      
                      agent = ValidationAgent()
                      result = await agent.validation_node({"invoice_id": "inv_dup"})
                      
                      assert result["current_state"] == InvoiceStatus.EXCEPTION
                      assert result["validation_results"]["is_duplicate"] is True
