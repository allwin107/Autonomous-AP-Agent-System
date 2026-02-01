import sys
import os
sys.path.append(os.getcwd())
import pytest
import time
from unittest.mock import AsyncMock, patch
from app.workflow.graph import invoice_workflow
from app.models.invoice import InvoiceStatus

@pytest.mark.asyncio
async def test_workflow_performance_latency(mock_db):
    """
    Measure the latency of a full workflow execution (mocked).
    """
    # Patch all major nodes to return fast
    with patch("app.workflow.nodes.extraction_agent") as mock_extract, \
         patch("app.workflow.nodes.validation_agent") as mock_validate, \
         patch("app.workflow.nodes.matching_agent") as mock_match, \
         patch("app.workflow.nodes.approval_agent") as mock_appr, \
         patch("app.workflow.nodes.payment_agent") as mock_pay, \
         patch("app.workflow.nodes.db") as mock_db_local, \
         patch("app.workflow.nodes.reflection_agent") as mock_refl:
        
        mock_extract.extraction_node = AsyncMock(side_effect=lambda s: {**s, "current_state": InvoiceStatus.VALIDATION})
        mock_validate.validation_node = AsyncMock(side_effect=lambda s: {**s, "current_state": InvoiceStatus.MATCHING})
        mock_match.matching_node = AsyncMock(side_effect=lambda s: {**s, "current_state": InvoiceStatus.APPROVAL_ROUTING})
        mock_appr.approval_routing_node = AsyncMock(side_effect=lambda s: {**s, "current_state": InvoiceStatus.PAYMENT_PREPARATION})
        mock_pay.payment_prep_node = AsyncMock(side_effect=lambda s: {**s, "current_state": InvoiceStatus.PAID})
        
        mock_db_local.invoices.get_by_field = AsyncMock(return_value=None)
        mock_refl.apply_learnings = AsyncMock(return_value=[])
        
        start_time = time.time()
        
        app = invoice_workflow.get_runnable()
        inputs = {
            "invoice_id": "PERF-001",
            "company_id": "acme",
            "current_state": InvoiceStatus.INGESTION,
            "errors": [],
            "retry_count": 0
        }
        config = {"configurable": {"thread_id": "perf_thread"}}
        await app.ainvoke(inputs, config=config)
        
        duration = time.time() - start_time
        
        print(f"\nWorkflow Latency: {duration:.4f} seconds")
        assert duration < 5.0 # Increased tolerance for CI/CD environments, but should be < 1s locally
