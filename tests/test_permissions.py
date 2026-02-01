import sys
import os
sys.path.append(os.getcwd())
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.guardrails.permissions import PermissionChecker, Role, Permission
from app.api.auth import User

@pytest.fixture
def permissions():
    return PermissionChecker()

def test_rbac_check(permissions):
    # Admin
    admin = User(username="admin", role="admin")
    assert permissions.check_permission(admin, Permission.APPROVE_INVOICE) is True
    assert permissions.check_permission(admin, Permission.MANAGE_USERS) is True

    # Finance Manager
    fin_man = User(username="cfo", role="finance_manager")
    assert permissions.check_permission(fin_man, Permission.APPROVE_INVOICE) is True
    assert permissions.check_permission(fin_man, Permission.PROCESS_PAYMENT) is True
    assert permissions.check_permission(fin_man, Permission.MANAGE_USERS) is False
    
    # Standard User
    user = User(username="u1", role="user")
    assert permissions.check_permission(user, Permission.CREATE_INVOICE) is True
    assert permissions.check_permission(user, Permission.APPROVE_INVOICE) is False

@pytest.mark.asyncio
async def test_sod_violation(permissions):
    # Mock DB Query for Audit
    with patch("app.guardrails.permissions.db") as mock_db:
        # Scenario: "creator" created the invoice
        mock_audit_cursor = MagicMock()
        mock_audit_cursor.to_list = AsyncMock(return_value=[
            {
                "actor": {"id": "creator"},
                "action": {"action_type": "USER_ACTION", "details": "Uploaded invoice"}
            }
        ])
        mock_db.db["audit_events"].find.return_value = mock_audit_cursor
        
        # 1. Creator attempts to Approve
        invoice_id = "inv_123"
        creator_user = User(username="creator", role="approver") # Promoted to approver? Or misconfigured role logic but SoD stops them.
        
        allowed = await permissions.check_sod(invoice_id, creator_user, "approve")
        assert allowed is False # SoD Violation
        
        # 2. Other Approver attempts to Approve
        other_user = User(username="other_approver", role="approver")
        allowed = await permissions.check_sod(invoice_id, other_user, "approve")
        assert allowed is True

def test_approval_limits(permissions):
    fin_man = User(username="cfo", role="finance_manager") # Limit 100k
    approver = User(username="mgr", role="approver") # Limit 10k
    
    assert permissions.check_approval_limit(fin_man, 50000.0) is True
    assert permissions.check_approval_limit(fin_man, 150000.0) is False
    
    assert permissions.check_approval_limit(approver, 5000.0) is True
    assert permissions.check_approval_limit(approver, 15000.0) is False
