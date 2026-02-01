import sys
import os
sys.path.append(os.getcwd())
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from app.agents.approval import ApprovalAgent
from app.models.invoice import InvoiceStatus, InvoiceData
from app.models.config import ApprovalRule, ApprovalMatrix, CompanyConfig

@pytest.mark.asyncio
async def test_approval_routing_logic():
    with patch("app.agents.approval.db") as mock_db:
        # Mock Invoice (High Value)
        mock_invoice = MagicMock()
        mock_invoice.invoice_id = "inv_approve_1"
        mock_invoice.company_id = "acme"
        data = InvoiceData(
            vendor_name="Big Corp", invoice_number="100", invoice_date=datetime.now(), total=15000.0
        )
        mock_invoice.data = data
        mock_db.invoices.get_by_field = AsyncMock(return_value=mock_invoice)
        mock_db.invoices.update = AsyncMock()
        
        # Mock Config
        # Rules:
        # 0 - 1000: dept_head
        # 1000 - 10000: finance_mgr
        # 10000 - 50000: finance_mgr, cfo
        
        rules = [
            ApprovalRule(rule_id="r1", amount_min=0, amount_max=1000, specific_approvers=["dept_head"]),
            ApprovalRule(rule_id="r2", amount_min=1000, amount_max=10000, specific_approvers=["finance_mgr"]),
            ApprovalRule(rule_id="r3", amount_min=10000, amount_max=50000, specific_approvers=["finance_mgr", "cfo"]) # Both needed? Or pool? 
            # Our logic in code is "Matches rule -> Add required". 
            # If logic matches multiple rules? (e.g. > 0 and > 10000?)
            # Usually disjoint.
        ]
        matrix = ApprovalMatrix(rules=rules)
        config = CompanyConfig(company_id="acme", company_name="Acme", approval_matrix=matrix)
        mock_db.config.get_by_field = AsyncMock(return_value=config)
        
        # Mock Notification
        with patch("app.agents.approval.notification_tool") as mock_notify:
            mock_notify.send_notification = AsyncMock()
            
            agent = ApprovalAgent()
            state = {"invoice_id": "inv_approve_1", "company_id": "acme"}
            result = await agent.approval_routing_node(state)
            
            # 15000 should match r3
            assert result["current_state"] == InvoiceStatus.AWAITING_APPROVAL
            mock_notify.send_notification.assert_called_once()
            
            # Check arguments
            args, _ = mock_notify.send_notification.call_args
            approvers = args[0]
            assert "cfo" in approvers
            assert "finance_mgr" in approvers

@pytest.mark.asyncio
async def test_determine_approvers_logic():
    agent = ApprovalAgent()
    rules = [
        ApprovalRule(rule_id="r1", amount_min=0, amount_max=100),
        ApprovalRule(rule_id="r2", amount_min=100, amount_max=None, specific_approvers=["boss"])
    ]
    
    # 50 -> r1 (no specific)
    # 150 -> r2 (boss)
    
    approvers = agent._determine_approvers(150, rules)
    assert "boss" in approvers
    
    approvers_low = agent._determine_approvers(50, rules)
    assert not approvers_low # No specific defined
