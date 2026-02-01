import sys
import os
sys.path.append(os.getcwd())
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.workflow.graph import invoice_workflow
from app.models.invoice import InvoiceStatus

@pytest.mark.asyncio
async def test_workflow_execution_success():
    # Patch all agent nodes in nodes.py to avoid side effects
    with patch("app.workflow.nodes.extraction_agent") as mock_extract_agent, \
         patch("app.workflow.nodes.validation_agent") as mock_validate_agent, \
         patch("app.workflow.nodes.matching_agent") as mock_match_agent, \
         patch("app.workflow.nodes.approval_agent") as mock_appr_agent, \
         patch("app.workflow.nodes.payment_agent") as mock_pay_agent, \
         patch("app.workflow.nodes.reflection_agent") as mock_refl_agent, \
         patch("app.workflow.nodes.db") as mock_db:
        
        # Setup mocks
        mock_extract_agent.extraction_node = AsyncMock(side_effect=lambda s: {**s, "current_state": InvoiceStatus.VALIDATION, "invoice_data": {"total": 100}})
        mock_validate_agent.validation_node = AsyncMock(side_effect=lambda s: {**s, "current_state": InvoiceStatus.MATCHING, "validation_results": {"valid": True}})
        mock_match_agent.matching_node = AsyncMock(side_effect=lambda s: {**s, "current_state": InvoiceStatus.APPROVAL_ROUTING, "matching_results": {"match_status": "MATCHED"}})
        mock_appr_agent.approval_routing_node = AsyncMock(side_effect=lambda s: {**s, "current_state": InvoiceStatus.PAYMENT_PREPARATION})
        mock_pay_agent.payment_prep_node = AsyncMock(side_effect=lambda s: {**s, "current_state": InvoiceStatus.PAYMENT_SCHEDULED})
        
        mock_refl_agent.apply_learnings = AsyncMock(return_value=[])
        mock_db.invoices.get_by_field = AsyncMock(return_value=None)
        
        app = invoice_workflow.get_runnable()
        
        initial_state = {
            "invoice_id": "inv_flow_1",
            "company_id": "acme",
            "current_state": InvoiceStatus.INGESTION,
            "previous_state": None,
            "invoice_data": None,
            "validation_results": None,
            "matching_results": None,
            "payment_proposal": None,
            "risk_score": 0.0,
            "human_approval_required": False,
            "errors": [],
            "retry_count": 0
        }
        
        config = {"configurable": {"thread_id": "test_thread"}}
        result = await app.ainvoke(initial_state, config=config)
        
        assert result["current_state"] == InvoiceStatus.PAYMENT_SCHEDULED
        assert mock_extract_agent.extraction_node.called
        assert mock_validate_agent.validation_node.called

@pytest.mark.asyncio
async def test_workflow_exception_path():
    with patch("app.workflow.nodes.extraction_agent") as mock_extract_agent, \
         patch("app.workflow.nodes.reflection_agent") as mock_refl_agent, \
         patch("app.workflow.nodes.db") as mock_db:
        
        mock_extract_agent.extraction_node = AsyncMock(side_effect=lambda s: {**s, "current_state": InvoiceStatus.EXCEPTION, "errors": ["OCR Failed"]})
        mock_refl_agent.reflect_on_failure = AsyncMock()
        mock_db.invoices.get_by_field = AsyncMock(return_value=None)
        
        app = invoice_workflow.get_runnable()
        initial_state = {
            "invoice_id": "inv_fail_1",
            "company_id": "acme",
            "current_state": InvoiceStatus.INGESTION,
            "previous_state": None,
            "invoice_data": None,
            "validation_results": None,
            "matching_results": None,
            "payment_proposal": None,
            "risk_score": 0.0,
            "human_approval_required": False,
            "errors": [],
            "retry_count": 0
        }
        
        config = {"configurable": {"thread_id": "test_thread_fail"}}
        result = await app.ainvoke(initial_state, config=config)
        
        assert result["current_state"] == InvoiceStatus.EXCEPTION
        assert "OCR Failed" in result["errors"]
