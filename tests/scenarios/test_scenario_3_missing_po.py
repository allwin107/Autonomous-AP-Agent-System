import sys
import os
sys.path.append(os.getcwd())
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from app.agents.matching import MatchingAgent
from app.agents.po_creator import POCreator
from app.models.invoice import InvoiceStatus, InvoiceData, LineItem
from app.models.config import ValidationRules, CompanyConfig

@pytest.mark.asyncio
async def test_matching_non_po_high_value():
    with patch("app.agents.matching.db") as mock_db:
        # Config: Require PO above 1000
        mock_config = MagicMock()
        mock_config.validation_rules = ValidationRules(require_po_above=1000.0)
        mock_db.config.get_by_field = AsyncMock(return_value=mock_config)
        
        # Invoice: No PO, Amount 5000
        invoice_data = InvoiceData(
            vendor_name="Acme", invoice_number="INV1", invoice_date=datetime.now(), total=5000.0, currency="USD", 
            po_reference=None
        )
        mock_invoice = MagicMock()
        mock_invoice.data = invoice_data
        mock_db.invoices.get_by_field = AsyncMock(return_value=mock_invoice)
        mock_db.invoices.update = AsyncMock()
        
        agent = MatchingAgent()
        state = {"invoice_id": "inv_high", "company_id": "c1"}
        
        result = await agent.matching_node(state)
        
        # Expectation: AWAITING_APPROVAL (Non-PO)
        assert result["current_state"] == InvoiceStatus.AWAITING_APPROVAL
        assert result["matching_results"]["match_status"] == "NON_PO_APPROVAL_NEEDED"
        
        # Verify DB update call
        mock_db.invoices.update.assert_called()
        args = mock_db.invoices.update.call_args[0]
        assert args[0] == "inv_high"
        assert args[1]["status"] == InvoiceStatus.AWAITING_APPROVAL

@pytest.mark.asyncio
async def test_po_creator_retrospective():
    with patch("app.agents.po_creator.db") as mock_db:
        creator = POCreator()
        
        # Mock Invoice
        invoice_data = InvoiceData(
            vendor_name="Acme", vendor_id="ven1", invoice_number="INV1", 
            invoice_date=datetime.now(),
            total=5000.0, subtotal=5000.0, vat_amount=0.0, currency="USD", 
            line_items=[LineItem(item_id=1, description="Consulting", quantity=1, unit_price=5000, line_total=5000)]
        )
        mock_invoice = MagicMock()
        mock_invoice.data = invoice_data
        mock_db.invoices.get_by_field = AsyncMock(return_value=mock_invoice)
        mock_db.db["purchase_orders"].insert_one = AsyncMock()
        mock_db.invoices.update = AsyncMock()
        
        po = await creator.create_retrospective_po("inv_high", "c1", "manager1")
        
        assert po is not None
        assert po.po_number.startswith("PO-RETRO-")
        assert po.metadata["type"] == "RETROSPECTIVE"
        assert po.metadata["approved_by"] == "manager1"
        assert len(po.line_items) == 1
        
        # Verify Link call
        mock_db.invoices.update.assert_called()
        link_args = mock_db.invoices.update.call_args[0]
        assert link_args[1]["data.po_reference"] == po.po_number
