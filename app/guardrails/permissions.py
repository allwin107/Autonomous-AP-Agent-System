from enum import Enum
from typing import List, Optional
import logging
from app.api.auth import User
from app.database import db
from app.models.audit import Actor

logger = logging.getLogger(__name__)

class Permission(str, Enum):
    # Invoice Actions
    CREATE_INVOICE = "CREATE_INVOICE"
    VIEW_INVOICE = "VIEW_INVOICE"
    APPROVE_INVOICE = "APPROVE_INVOICE"
    REJECT_INVOICE = "REJECT_INVOICE"
    
    # Financial Actions
    PROCESS_PAYMENT = "PROCESS_PAYMENT"
    CREATE_JOURNAL = "CREATE_JOURNAL"
    
    # Admin
    CONFIGURE_SYSTEM = "CONFIGURE_SYSTEM"
    MANAGE_USERS = "MANAGE_USERS"
    VIEW_AUDIT = "VIEW_AUDIT"

class Role(str, Enum):
    ADMIN = "admin"
    FINANCE_MANAGER = "finance_manager" # Can approve + pay (with limits)
    APPROVER = "approver" # Can approve
    USER = "user" # Can view/create
    AGENT = "agent" # System agent
    SYSTEM = "system"

# Role -> Permissions Mapping
ROLE_PERMISSIONS = {
    Role.ADMIN: [p for p in Permission], # All
    Role.FINANCE_MANAGER: [
        Permission.VIEW_INVOICE, Permission.APPROVE_INVOICE, Permission.REJECT_INVOICE,
        Permission.PROCESS_PAYMENT, Permission.VIEW_AUDIT, Permission.CREATE_JOURNAL
    ],
    Role.APPROVER: [
        Permission.VIEW_INVOICE, Permission.APPROVE_INVOICE, Permission.REJECT_INVOICE
    ],
    Role.USER: [
        Permission.CREATE_INVOICE, Permission.VIEW_INVOICE
    ],
    Role.AGENT: [
        Permission.VIEW_INVOICE, Permission.CREATE_JOURNAL, Permission.PROCESS_PAYMENT # Agents often automate these
    ]
}

class PermissionChecker:
    def __init__(self):
        pass

    def check_permission(self, user: User, permission: Permission) -> bool:
        """
        Basic Role-Based Check.
        """
        # Map user.role (string) to Role Enum
        try:
            role_enum = Role(user.role)
        except ValueError:
            # Fallback for unknown roles
            logger.warning(f"Unknown role {user.role} for user {user.username}")
            return False

        allowed = ROLE_PERMISSIONS.get(role_enum, [])
        if permission in allowed:
            return True
            
        logger.warning(f"User {user.username} ({user.role}) denied permission {permission}")
        return False

    async def check_sod(self, invoice_id: str, user: User, action: str) -> bool:
        """
        Segregation of Duties Check.
        Rules:
        1. Creator cannot Approve.
        2. Approver cannot Pay (maybe - depends on policy, let's enforce STRICT).
        
        Returns True if SoD check result is PASS (Safe).
        Returns False if SoD Violation.
        """
        # 1. Fetch Audit Logs for this invoice
        # We look for "USER_ACTION" types.
        # Ideally using the AuditService, but direct DB access here for speed/simplicity
        
        # Who Created/Uploaded?
        # ActionType: USER_ACTION, Details like "Uploaded..." or "Created..."
        # Or check invoice.created_by if we store it (we assume audit log is source of truth)
        
        cursor = db.db["audit_events"].find({
            "invoice_id": invoice_id,
            "action.performed_by.type": "USER"
        })
        
        history_actions = await cursor.to_list(100)
        
        creators = set()
        approvers = set()
        
        for event in history_actions:
            act_type = event.get("action", {}).get("action_type")
            details = event.get("action", {}).get("details", "").upper()
            actor_name = event.get("actor", {}).get("id")
            
            if "UPLOAD" in details or "CREATED" in details:
                creators.add(actor_name)
            
            if "APPROVE" in details or act_type == "APPROVE":
                approvers.add(actor_name)
                
        # Rule 1: Creator cannot Approve
        if action.lower() == "approve":
            if user.username in creators:
                logger.warning(f"SoD Violation: User {user.username} created invoice {invoice_id} and cannot approve it.")
                return False

        # Rule 2: Approver cannot Process Payment
        # If action is "Process Payment": if user in approvers -> False?
        # Some companies allow Finance Mgr to do both. Let's assume STRICT SoD.
        if action.lower() == "process_payment":
            if user.username in approvers:
                 logger.warning(f"SoD Violation: User {user.username} approved invoice {invoice_id} and cannot process payment.")
                 return False
                 
        return True

    def check_approval_limit(self, user: User, amount: float) -> bool:
        """
        Check if user has sufficient limit.
        """
        # In a real system, limits are in User/Profile DB.
        # Mocking logic based on role/username
        
        if user.role == Role.ADMIN.value:
            return True # Unlimited
            
        if user.role == Role.FINANCE_MANAGER.value:
            return amount < 100000.0
            
        if user.role == Role.APPROVER.value:
             return amount < 10000.0
             
        # Standard users cannot approve (handled by check_permission generally, but if they got here...)
        return False

permission_checker = PermissionChecker()
