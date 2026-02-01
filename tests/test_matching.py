import sys
import os
sys.path.append(os.getcwd())
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from app.agents.matching import MatchingAgent
from app.models.invoice import InvoiceStatus, InvoiceData, LineItem
from app.models.purchase_order import PurchaseOrder, POStatus
from app.models.grn import GoodsReceiptNote, GRNStatus
from app.models.config import MatchingTolerances

@pytest.mark.asyncio
async def test_matching_success():
    with patch("app.agents.matching.db") as mock_db:
        # Mock Invoice
        mock_invoice = MagicMock()
        mock_invoice.invoice_id = "inv_match"
        mock_invoice.company_id = "acme"
        data = InvoiceData(
            vendor_name="ABC", 
            invoice_number="123", 
            invoice_date=datetime.now(), 
            total=100.0, 
            subtotal=100.0,
            po_reference="PO-100",
            line_items=[
                LineItem(item_id=1, description="Widget", quantity=10, unit_price=10.0, line_total=100.0)
            ]
        )
        mock_invoice.data = data
        mock_db.invoices.get_by_field = AsyncMock(return_value=mock_invoice)
        mock_db.invoices.update = AsyncMock()
        
        # Mock Config (Tolerances)
        mock_config = MagicMock()
        mock_config.matching_tolerances = MatchingTolerances()
        mock_db.config.get_by_field = AsyncMock(return_value=mock_config)
        
        # Mock PO
        po_doc = {
            "po_number": "PO-100",
            "company_id": "acme",
            "vendor_id": "ven_1",
            "vendor_name": "ABC",
            "requester_email": "a@a.com",
            "department": "IT",
            "po_date": datetime.now(),
            "subtotal": 100.0, "vat_amount": 0.0, "total": 100.0,
            "status": "ISSUED",
            "line_items": [
                {"item_id": 1, "description": "Widget", "quantity": 10, "unit_price": 10.0, "line_total": 100.0}
            ]
        }
        mock_db.db.__getitem__.return_value.find_one = AsyncMock(return_value=po_doc)
        
        # Mock GRN (Perfect match)
        grn_doc = {
            "grn_number": "GRN-1",
            "po_number": "PO-100",
            "company_id": "acme",
            "vendor_id": "ven_1",
            "received_by": "User",
            "status": "RECEIVED",
            "line_items": [
                {"item_id": 1, "description": "Widget", "quantity": 10, "unit_price": 0.0, "line_total": 0.0}
            ]
        }
        mock_cursor = AsyncMock()
        mock_cursor.to_list.return_value = [grn_doc]
        mock_db.db.__getitem__.return_value.find.return_value = mock_cursor
        
        agent = MatchingAgent()
        state = {"invoice_id": "inv_match", "company_id": "acme"}
        result = await agent.matching_node(state)
        
        assert result["current_state"] == InvoiceStatus.PAYMENT_PREPARATION
        assert result["matching_results"]["match_status"] == "MATCHED"

@pytest.mark.asyncio
async def test_matching_variance_price():
    with patch("app.agents.matching.db") as mock_db:
        # Invoice Price 12.0 vs PO 10.0 (20% diff > 2% tolerance)
        mock_invoice = MagicMock()
        data = InvoiceData(
            vendor_name="ABC", invoice_number="123", invoice_date=datetime.now(), total=120.0, subtotal=120.0, po_reference="PO-100",
            line_items=[LineItem(item_id=1, description="Widget", quantity=10, unit_price=12.0, line_total=120.0)]
        )
        mock_invoice.data = data
        mock_db.invoices.get_by_field = AsyncMock(return_value=mock_invoice)
        mock_db.invoices.update = AsyncMock()
        mock_db.config.get_by_field = AsyncMock(return_value=MagicMock(matching_tolerances=MatchingTolerances()))
        
        po_doc = {
            "po_number": "PO-100", "company_id": "acme", "vendor_id": "ven_1", "vendor_name": "ABC", "requester_email": "a@a.com", "department": "IT", "po_date": datetime.now(),
            "subtotal": 100.0, "vat_amount": 0.0, "total": 100.0, "status": "ISSUED",
            "line_items": [{"item_id": 1, "description": "Widget", "quantity": 10, "unit_price": 10.0, "line_total": 100.0}]
        }
        mock_db.db.__getitem__.return_value.find_one = AsyncMock(return_value=po_doc)
        
        grn_doc = {
            "grn_number": "GRN-1", "po_number": "PO-100", "company_id": "acme", "vendor_id": "ven_1", "received_by": "User", "status": "RECEIVED",
            "line_items": [{"item_id": 1, "description": "Widget", "quantity": 10, "unit_price": 0.0, "line_total": 0.0}]
        }
        mock_cursor = AsyncMock()
        mock_cursor.to_list.return_value = [grn_doc]
        mock_db.db.__getitem__.return_value.find.return_value = mock_cursor
        
        agent = MatchingAgent()
        state = {"invoice_id": "inv_var", "company_id": "acme"}
        result = await agent.matching_node(state)
        
        assert result["current_state"] == InvoiceStatus.AWAITING_APPROVAL
        assert result["matching_results"]["match_status"] == "VARIANCE"
        assert "Price variance" in result["matching_results"]["details"]

@pytest.mark.asyncio
async def test_matching_missing_po_ref():
    with patch("app.agents.matching.db") as mock_db:
        mock_invoice = MagicMock()
        # High value, so PO required
        data = InvoiceData(vendor_name="ABC", invoice_number="123", invoice_date=datetime.now(), total=100000.0, subtotal=100000.0, po_reference=None)
        mock_invoice.data = data
        mock_db.invoices.get_by_field = AsyncMock(return_value=mock_invoice)
        mock_db.invoices.update = AsyncMock()
        
        rule_config = MagicMock()
        rule_config.validation_rules.require_po_above = 50000.0
        mock_db.config.get_by_field = AsyncMock(return_value=rule_config)
        
        agent = MatchingAgent()
        state = {"invoice_id": "inv_no_po", "company_id": "acme"}
        result = await agent.matching_node(state)
        
        assert result["current_state"] == InvoiceStatus.EXCEPTION
        assert result["matching_results"]["match_status"] == "NO_PO"
