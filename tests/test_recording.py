import sys
import os
sys.path.append(os.getcwd())
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from app.agents.recording import RecordingAgent
from app.models.invoice import InvoiceStatus, InvoiceData, LineItem
from app.models.config import GLMapping
from app.models.accounting import EntryType

@pytest.mark.asyncio
async def test_journal_entry_creation():
    with patch("app.agents.recording.db") as mock_db:
        # Mock Invoice
        mock_invoice = MagicMock()
        mock_invoice.invoice_id = "inv_rec"
        mock_invoice.company_id = "acme"
        mock_invoice.vendor_id = "v1"
        
        data = InvoiceData(
            vendor_name="Office Co", 
            invoice_number="100", 
            invoice_date=datetime.now(),
            total=1200.0, 
            subtotal=1000.0,
            vat_amount=200.0,
            currency="GBP",
            line_items=[
                LineItem(item_id=1, description="Pens", quantity=100, unit_price=10, line_total=1000.0, category="Office Supplies")
            ]
        )
        mock_invoice.data = data
        mock_db.invoices.get_by_field = AsyncMock(return_value=mock_invoice)
        
        # Mock Config
        mock_config = MagicMock()
        mock_config.gl_mapping = GLMapping() # Use defaults (7400 for Office Supplies)
        mock_db.config.get_by_field = AsyncMock(return_value=mock_config)
        
        mock_db.db["journal_entries"].insert_one = AsyncMock()
        mock_db.db["vendors"].update_one = AsyncMock()
        mock_db.invoices.update = AsyncMock()
        
        agent = RecordingAgent()
        state = {"invoice_id": "inv_rec", "company_id": "acme"}
        
        result = await agent.recording_node(state)
        
        # Verify calls
        mock_db.db["journal_entries"].insert_one.assert_called_once()
        je_dump = mock_db.db["journal_entries"].insert_one.call_args[0][0]
        
        # Verify Journal Entry Structure
        # DR 1000 (Expense) + DR 200 (VAT) = CR 1200 (AP)
        lines = je_dump["lines"]
        assert len(lines) == 3 # Expense, VAT, AP
        
        # Check Expense Line
        exp_line = next(l for l in lines if l["account_name"] == "Office Supplies")
        assert exp_line["gl_code"] == "7400"
        assert exp_line["amount"] == 1000.0
        assert exp_line["type"] == EntryType.DEBIT
        
        # Check VAT
        vat_line = next(l for l in lines if l["account_name"] == "VAT Recoverable")
        assert vat_line["gl_code"] == "1510"
        assert vat_line["amount"] == 200.0
        assert vat_line["type"] == EntryType.DEBIT
        
        # Check AP
        ap_line = next(l for l in lines if l["account_name"] == "Accounts Payable")
        assert ap_line["gl_code"] == "2100"
        assert ap_line["amount"] == 1200.0
        assert ap_line["type"] == EntryType.CREDIT

        assert je_dump["total_debit"] == 1200.0
        assert je_dump["total_credit"] == 1200.0
