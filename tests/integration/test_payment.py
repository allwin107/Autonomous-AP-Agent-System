import sys
import os
sys.path.append(os.getcwd())
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from app.agents.payment import PaymentAgent
from app.models.invoice import InvoiceStatus, InvoiceData
from app.models.vendor import Vendor, BankDetails

@pytest.mark.asyncio
async def test_payment_prep_success():
    with patch("app.agents.payment.db") as mock_db:
        # Mock Invoice
        mock_invoice = MagicMock()
        mock_invoice.invoice_id = "inv_pay"
        mock_invoice.company_id = "acme"
        data = InvoiceData(
            vendor_name="Honest Co", invoice_number="100", invoice_date=datetime.now(), total=500.0, currency="GBP"
        )
        mock_invoice.data = data
        mock_db.invoices.get_by_field = AsyncMock(return_value=mock_invoice)
        mock_db.invoices.update = AsyncMock()
        
        # Mock Vendor with Bank Details (old enough)
        bank = BankDetails(
            account_name="Honest Co", account_number="12345678", sort_code="10-10-10", 
            last_updated=datetime(2020, 1, 1) # Old
        )
        vendor = Vendor(
            vendor_id="v1", company_id="acme", name="Honest Co", bank_details=bank, payment_terms="NET30"
        )
        # Mock find_one for vendor
        mock_collection = MagicMock()
        mock_collection.find_one = AsyncMock(return_value=vendor.model_dump())
        
        # When db.db["vendors"] is accessed, return mock_collection
        mock_db.db.__getitem__.return_value = mock_collection
        
        agent = PaymentAgent()
        
        # Bypass DB lookup for vendor
        agent._find_vendor = AsyncMock(return_value=vendor)
        
        state = {"invoice_id": "inv_pay", "company_id": "acme"}
        result = await agent.payment_prep_node(state)
        

        
        assert result["current_state"] == InvoiceStatus.PAID
        assert result["payment_details"]["status"] == "SCHEDULED"

@pytest.mark.asyncio
async def test_bank_change_fraud_check():
    agent = PaymentAgent()
    
    # Recent Change
    bank = BankDetails(
        account_name="Honest Co", account_number="12345678", 
        last_updated=datetime.utcnow() # NOW
    )
    vendor = Vendor(
        vendor_id="v1", company_id="acme", name="Honest Co", bank_details=bank
    )
    
    assert agent._check_bank_details_change(vendor) == True

    # Old Change
    bank.last_updated = datetime(2020, 1, 1)
    assert agent._check_bank_details_change(vendor) == False
