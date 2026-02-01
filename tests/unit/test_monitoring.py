import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.monitoring.metrics import metrics_engine
from app.models.invoice import InvoiceStatus

@pytest.mark.asyncio
async def test_get_system_health():
    with patch("app.monitoring.metrics.db") as mock_db:
        # Mock status counts
        mock_pipeline_res = [{"_id": InvoiceStatus.PAID, "count": 10}, {"_id": InvoiceStatus.EXCEPTION, "count": 2}]
        mock_24h_res = [{"total": 12, "exceptions": 2, "paid": 10}]
        
        # Configure the chain: .collection.aggregate().to_list()
        mock_cursor_1 = MagicMock()
        mock_cursor_1.to_list = AsyncMock(return_value=mock_pipeline_res)
        
        mock_cursor_2 = MagicMock()
        mock_cursor_2.to_list = AsyncMock(return_value=mock_24h_res)
        
        mock_db.invoices.collection.aggregate.side_effect = [mock_cursor_1, mock_cursor_2]
        
        health = await metrics_engine.get_system_health("acme_corp")
        
        assert health["total_invoices"] == 12
        assert health["active_exceptions"] == 2
        assert health["last_24h"]["success_rate"] == 83.33

@pytest.mark.asyncio
async def test_get_agent_performance():
    with patch("app.monitoring.metrics.db") as mock_db:
        mock_res = [
            {"_id": True, "count": 100},
            {"_id": False, "count": 5}
        ]
        mock_cursor = MagicMock()
        mock_cursor.to_list = AsyncMock(return_value=mock_res)
        mock_db.audit.collection.aggregate.return_value = mock_cursor
        
        perf = await metrics_engine.get_agent_performance("extraction_agent", "acme_corp")
        
        assert perf["total_actions"] == 105
        assert perf["success_rate"] == 95.24

@pytest.mark.asyncio
async def test_get_sla_compliance():
    with patch("app.monitoring.metrics.db") as mock_db:
        mock_res = [
            {"_id": "COMPLIANT", "count": 50},
            {"_id": "BREACHED", "count": 5}
        ]
        mock_cursor = MagicMock()
        mock_cursor.to_list = AsyncMock(return_value=mock_res)
        mock_db.invoices.collection.aggregate.return_value = mock_cursor
        
        sla = await metrics_engine.get_sla_compliance("acme_corp")
        
        assert sla["COMPLIANT"] == 50
        assert sla["BREACHED"] == 5
        assert sla["AT_RISK"] == 0
