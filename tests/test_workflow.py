import sys
import os
sys.path.append(os.getcwd())
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.workflow.graph import invoice_workflow
from app.workflow.state import InvoiceState
from app.models.invoice import InvoiceStatus

@pytest.mark.asyncio
async def test_workflow_execution_success():
    # Mocking agents via nodes.py imports wouldn't work easily since graph imports them
    # Better to mock the agent instances themselves as they are imported in nodes.py
    
    with patch("app.agents.extraction.extraction_agent.extraction_node") as mock_extract:
        with patch("app.agents.validation.validation_agent.validation_node") as mock_validate:
            
            # Setup mocks to return modified state
            async def mock_extract_side_effect(state):
                state["current_state"] = InvoiceStatus.VALIDATION
                state["invoice_data"] = {"total": 100}
                return state
            
            async def mock_validate_side_effect(state):
                state["current_state"] = InvoiceStatus.MATCHING
                state["validation_results"] = {"valid": True}
                return state
            
            mock_extract.side_effect = mock_extract_side_effect
            mock_validate.side_effect = mock_validate_side_effect
            
            # Initialize Workflow Runnable
            app = invoice_workflow.get_runnable()
            
            # Initial State
            initial_state = InvoiceState(
                invoice_id="inv_flow_1",
                company_id="acme",
                current_state=InvoiceStatus.INGESTION,
                previous_state=None,
                invoice_data=None,
                validation_results=None,
                matching_results=None,
                payment_proposal=None,
                risk_score=0.0,
                human_approval_required=False,
                errors=[],
                retry_count=0
            )
            
            # Run Graph
            config = {"configurable": {"thread_id": "test_thread"}}
            result = await app.ainvoke(initial_state, config=config)
            
            # Assertions
            # Flow: Ingestion -> Extraction -> Validation -> Matching -> Approval -> Payment -> End
            # With our mocks, it should reach Payment Scheduled
            
            assert result["current_state"] == InvoiceStatus.PAYMENT_SCHEDULED
            assert result["invoice_data"]["total"] == 100
            
            # Check call counts to verify path
            mock_extract.assert_called_once()
            mock_validate.assert_called_once()

@pytest.mark.asyncio
async def test_workflow_exception_path():
    with patch("app.agents.extraction.extraction_agent.extraction_node") as mock_extract:
         async def mock_extract_fail(state):
             state["current_state"] = InvoiceStatus.EXCEPTION
             state["errors"] = ["OCR Failed"]
             return state
         
         mock_extract.side_effect = mock_extract_fail
         
         app = invoice_workflow.get_runnable()
         initial_state = InvoiceState(
            invoice_id="inv_fail_1",
            company_id="acme",
            current_state=InvoiceStatus.INGESTION,
            previous_state=None,
            invoice_data=None,
            validation_results=None,
            matching_results=None,
            payment_proposal=None,
            risk_score=0.0,
            human_approval_required=False,
            errors=[],
            retry_count=0
        )
         
         config = {"configurable": {"thread_id": "test_thread_fail"}}
         result = await app.ainvoke(initial_state, config=config)
         
         assert result["current_state"] == InvoiceStatus.EXCEPTION
         assert "OCR Failed" in result["errors"]
