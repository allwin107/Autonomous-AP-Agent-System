import pytest
import os
import sys
sys.path.append(os.getcwd())
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from app.agents.matching import MatchingAgent
from app.models.invoice import InvoiceStatus

@pytest.mark.asyncio
async def test_scenario_4_matching_mismatch(mock_db, sample_invoice):
    """
    Scenario 4: Discrepancy between invoice and purchase order.
    """
    agent = MatchingAgent()
    
    # 1. Setup Invoice with a specific amount
    sample_invoice.data.total = 150.0
    sample_invoice.data.po_reference = "PO-777"
    mock_db.invoices.get_by_field.return_value = sample_invoice
    
    # 2. Setup Purchase Order with a DIFFERENT amount (Raw DB Mock)
    po_doc = {
        "po_number": "PO-777",
        "company_id": "acme",
        "vendor_id": "v1",
        "vendor_name": "Acme",
        "requester_email": "user@acme.com",
        "department": "Finance",
        "po_date": datetime.now(),
        "subtotal": 100.0,
        "vat_amount": 0.0,
        "total": 100.0,
        "status": "ISSUED",
        "line_items": []
    }
    
    with patch("app.agents.matching.db") as mock_db_local:
        mock_db_local.invoices = mock_db.invoices
        mock_db_local.db.__getitem__.return_value.find_one = AsyncMock(return_value=po_doc)
        mock_db_local.db.__getitem__.return_value.find.return_value = AsyncMock() # For GRN
        mock_db_local.db.__getitem__.return_value.find.return_value.to_list = AsyncMock(return_value=[])
        mock_config = MagicMock()
        mock_config.matching_tolerances.price_variance_percent = 5.0
        mock_config.matching_tolerances.total_amount_variance = 1.0
        mock_db_local.config.get_by_field = AsyncMock(return_value=mock_config)
        
        # 3. Run matching
        state = {"invoice_id": sample_invoice.invoice_id, "company_id": "acme"}
        result = await agent.matching_node(state)
        
        # 4. Assertions
        assert result["current_state"] == InvoiceStatus.AWAITING_APPROVAL
        assert result["matching_results"]["match_status"] == "VARIANCE"
