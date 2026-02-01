import sys
import os
sys.path.append(os.getcwd())
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from app.guardrails.audit_logger import AuditLogger
from app.models.audit import ActionType

@pytest.mark.asyncio
async def test_log_event():
    with patch("app.guardrails.audit_logger.db") as mock_db:
        mock_db.audit.create = AsyncMock()
        
        logger = AuditLogger()
        actor = {"id": "user1", "name": "Test User", "type": "USER"}
        
        await logger.log_event(
            invoice_id="inv_test",
            event_type="APPROVAL", # String conversion check
            actor=actor,
            action_details="Approved invoice",
            metadata={"company_id": "acme"}
        )
        
        mock_db.audit.create.assert_called_once()
        event = mock_db.audit.create.call_args[0][0]
        assert event.invoice_id == "inv_test"
        assert event.model_dump()["action"]["action_type"] == ActionType.USER_ACTION # Fallback or matched?
        # Actually in my code: if string matches enum, it uses it. "APPROVAL" is not in ActionType enum (USER_ACTION, AGENT_DECISION, etc).
        # Wait, ActionType enum in `models/audit.py`: SYSTEM_EVENT, USER_ACTION, AGENT_DECISION, API_CALL, ERROR, STATE_CHANGE
        # My code does `try ActionType(event_type) except: USER_ACTION`. "APPROVAL" isn't a valid enum value. So it falls back to USER_ACTION.
        assert event.action.action_type == ActionType.USER_ACTION
        assert event.action.details == "Approved invoice"

@pytest.mark.asyncio
async def test_log_decision():
    with patch("app.guardrails.audit_logger.db") as mock_db:
        mock_db.audit.create = AsyncMock()
        logger = AuditLogger()
        
        await logger.log_decision(
            invoice_id="inv_ai",
            made_by="ValidationAgent",
            reasoning="Looks good",
            options=["Approve", "Reject"],
            chosen="Approve",
            metadata={"company_id": "acme"}
        )
        
        mock_db.audit.create.assert_called_once()
        event = mock_db.audit.create.call_args[0][0]
        assert event.decision is not None
        assert event.decision.chosen_option == "Approve"
        assert event.action.action_type == ActionType.AGENT_DECISION

@pytest.mark.asyncio
async def test_generate_report_pdf():
    # Mock get_audit_trail to return events
    logger = AuditLogger()
    
    # Mock db fetch
    with patch("app.guardrails.audit_logger.db") as mock_db:
        mock_cursor = MagicMock()
        # Mock event data
        evt_data = {
            "event_id": "1",
            "invoice_id": "inv_1",
            "company_id": "c1",
            "timestamp": datetime.now(),
            "actor": {"id": "u1", "name": "User", "type": "USER"},
            "action": {"action_type": "USER_ACTION", "performed_by": {"id": "u1", "name": "User", "type": "USER"}, "details": "Test Action"}
        }
        mock_cursor.to_list = AsyncMock(return_value=[evt_data]) 
        mock_db.db["audit_events"].find.return_value.sort.return_value = mock_cursor
        
        # Test PDF generation
        filename = await logger.generate_audit_report("inv_1", "PDF")
        assert filename.endswith(".pdf")
        
        # Cleanup
        if os.path.exists(filename):
            os.remove(filename)
