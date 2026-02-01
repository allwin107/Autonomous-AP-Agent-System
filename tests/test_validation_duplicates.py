import sys
import os
sys.path.append(os.getcwd())
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from app.agents.validation import ValidationAgent
from app.models.invoice import InvoiceData, LineItem, InvoiceStatus

@pytest.mark.asyncio
async def test_duplicate_exact():
    with patch("app.agents.validation.db") as mock_db, \
         patch("app.agents.validation.duplicate_detector") as mock_detector, \
         patch("app.agents.validation.vat_validator"), \
         patch("app.agents.validation.fraud_detector"):
         
        # Mock Detector Response
        mock_detector.check_duplicates = AsyncMock(return_value={
            "is_duplicate": True,
            "match_type": "EXACT_NUMBER",
            "conflicting_invoice_id": "inv_old",
            "confidence": 1.0
        })
        
        # Mock VAT/Fraud defaults
        mock_vat = MagicMock()
        mock_vat.validate_vat.return_value = {"valid": True}
        
        # Setup Invoice
        agent = ValidationAgent()
        # Ensure InvoiceData is complete if needed
        invoice_data = InvoiceData(
            vendor_name="Acme", invoice_number="100", invoice_date=datetime.now(), total=100.0, currency="GBP"
        )
        mock_invoice = MagicMock()
        # Mock data as object
        mock_invoice.data = invoice_data
        
        mock_db.invoices.get_by_field = AsyncMock(return_value=mock_invoice)
        mock_db.vendors.get_by_field = AsyncMock(return_value=None)
        mock_db.invoices.update = AsyncMock()

        state = {"invoice_id": "inv_new"}
        # If vat_validator methods are called on the class instance in the agent code?
        # In validation.py: vat_result = vat_validator.validate_vat(data)
        # We patched "app.agents.validation.vat_validator". The imported object is a mock.
        # But we need to set the specific method return value on that mock.
        
        # The patch creates a MagicMock for the MODULE attribute 'vat_validator'
        # So agent.vat_validator is that mock.
        # We need to configure it.
        # The context manager returns the mock.
        # Wait, I didn't capture the return of patch("...vat_validator").
        # I should use: patch(...) as mock_vat.
        # I did: with patch(...) as mock_db, patch(...) as mock_detector, patch(...), patch(...)
        # The last two patches are active but not bound to variables.
        # I need to target the return_value of validate_vat.
        
        # Re-writing the test function to capture them correctly.
        pass

@pytest.mark.asyncio
async def test_duplicate_exact():
    with patch("app.agents.validation.db") as mock_db, \
         patch("app.agents.validation.duplicate_detector") as mock_detector, \
         patch("app.agents.validation.vat_validator") as mock_vat, \
         patch("app.agents.validation.fraud_detector") as mock_fraud:
         
        # Mock Detector Response
        mock_detector.check_duplicates = AsyncMock(return_value={
            "is_duplicate": True,
            "match_type": "EXACT_NUMBER",
            "conflicting_invoice_id": "inv_old",
            "confidence": 1.0
        })
        
        # Mock VAT/Fraud defaults
        mock_vat.validate_vat.return_value = {"valid": True}
        mock_fraud.analyze_fraud_risk.return_value = {"fraud_score": 0.0, "flags": []}
        
        # Setup Invoice
        agent = ValidationAgent()
        invoice_data = InvoiceData(
            vendor_name="Acme", invoice_number="100", invoice_date=datetime.now(), total=100.0, currency="GBP"
        )
        mock_invoice = MagicMock()
        mock_invoice.data = invoice_data
        mock_db.invoices.get_by_field = AsyncMock(return_value=mock_invoice)
        mock_db.vendors.get_by_field = AsyncMock(return_value=None)
        mock_db.invoices.update = AsyncMock()

        state = {"invoice_id": "inv_new"}
        # ensure mock_detector is used
        result = await agent.validation_node(state)
        
        # Check result
        if "errors" in result:
             print(f"Errors: {result['errors']}")
             
        assert result["current_state"] == InvoiceStatus.EXCEPTION
        assert result["validation_results"]["is_duplicate"] is True
        assert result["validation_results"]["duplicate_of_id"] == "inv_old"

@pytest.mark.asyncio
async def test_fuzzy_duplicate_items():
    with patch("app.tools.duplicate_detector.db") as mock_db:
        # We test the Detector logic directly for fuzzy matching
        from app.tools.duplicate_detector import duplicate_detector
        
        # Existing invoice in DB
        inv_existing = MagicMock()
        inv_existing.invoice_id = "inv_exist"
        inv_existing.status = InvoiceStatus.PAID
        inv_existing.data.line_items = [LineItem(item_id="1", description="Office Chairs", quantity=1, unit_price=100, line_total=100)]
        
        # Mock Find for Exact (None) and Fuzzy (Found)
        # First call is Exact (returns empty list)
        # Second call is Fuzzy (returns [inv_existing])
        
        mock_cursor_exact = AsyncMock()
        mock_cursor_exact.to_list = AsyncMock(return_value=[]) 
        # Actually duplicate_detector calls `find`.
        
        # To simulate find behavior with arguments:
        async def side_effect(query):
            if "invoice_number" in query.get("data.invoice_number", ""): # Exact check
                return []
            if "data.total" in query: # Fuzzy check
                return [inv_existing]
            return []

        mock_db.invoices.find.side_effect = side_effect
        
        # Check
        result = await duplicate_detector.check_duplicates(
            invoice_id="inv_new",
            vendor_name="Vendor",
            invoice_number="Different",
            total=100.0,
            invoice_date=datetime.now(),
            line_items=[LineItem(item_id="1", description="Office Chairs", quantity=1, unit_price=100, line_total=100)]
        )
        
        assert result["is_duplicate"] is True
        assert result["match_type"] == "FUZZY_PLUS_ITEMS"
        assert result["confidence"] > 0.9

