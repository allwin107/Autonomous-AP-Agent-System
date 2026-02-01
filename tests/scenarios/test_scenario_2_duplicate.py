import sys
import os
sys.path.append(os.getcwd())
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from app.agents.validation import ValidationAgent
from app.models.invoice import InvoiceData, LineItem, InvoiceStatus

@pytest.mark.asyncio
async def test_duplicate_exact(mock_db, sample_invoice):
    sample_invoice.invoice_id = "inv_dup"
    mock_db.invoices.get_by_field.return_value = sample_invoice
    
    # Mock Tools
    with patch("app.agents.validation.duplicate_detector") as mock_dup, \
         patch("app.agents.validation.vat_validator") as mock_vat, \
         patch("app.agents.validation.fraud_detector") as mock_fraud, \
         patch("app.agents.validation.db") as mock_db_local:
        
        mock_db_local.invoices = mock_db.invoices
        mock_db_local.vendors = mock_db.vendors
        
        mock_dup.check_duplicates = AsyncMock(return_value={"is_duplicate": True, "match_type": "EXACT", "conflicting_invoice_id": "OLD-123"})
        mock_fraud.check_bank_details_change = AsyncMock(return_value=False)
        mock_vat.validate_vat = MagicMock(return_value={"valid": True})
        mock_fraud.analyze_fraud_risk = MagicMock(return_value={"fraud_score": 0.0, "flags": []})
        
        agent = ValidationAgent()
        state = {
            "invoice_id": "inv_dup",
            "company_id": "acme",
            "current_state": "VALIDATION",
            "invoice_data": sample_invoice.data.model_dump(),
            "validation_results": None,
            "matching_results": None,
            "risk_score": 0.0,
            "human_approval_required": False,
            "errors": []
        }
        result = await agent.validation_node(state)
        
        assert result["current_state"] == InvoiceStatus.EXCEPTION
        assert result["validation_results"]["is_duplicate"] is True

@pytest.mark.asyncio
async def test_fuzzy_duplicate_items(mock_db):
    with patch("app.tools.duplicate_detector.db") as mock_db_local:
        from app.tools.duplicate_detector import duplicate_detector
        
        mock_db_local.invoices = mock_db.invoices
        
        # Existing invoice in DB
        inv_existing = MagicMock()
        inv_existing.invoice_id = "inv_exist"
        inv_existing.status = InvoiceStatus.PAID
        inv_existing.data.line_items = [LineItem(item_id=1, description="Office Chairs", quantity=1, unit_price=100, line_total=100)]
        
        # Mock .list()
        mock_db_local.invoices.list = AsyncMock(side_effect=lambda query: [inv_existing] if "data.total" in query else [])
        
        # Check
        result = await duplicate_detector.check_duplicates(
            invoice_id="inv_new",
            vendor_name="Vendor",
            invoice_number="Different",
            total=100.0,
            invoice_date=datetime.now(),
            line_items=[LineItem(item_id=1, description="Office Chairs", quantity=1, unit_price=100, line_total=100)]
        )
        
        assert result["is_duplicate"] is True
        assert result["match_type"] == "FUZZY_PLUS_ITEMS"
