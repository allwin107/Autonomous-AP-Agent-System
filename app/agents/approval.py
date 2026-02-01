import logging
from typing import Dict, Any, List

from app.database import db
from app.models.invoice import InvoiceStatus, InvoiceData
from app.models.config import ApprovalRule
from app.tools.notification_tool import notification_tool

logger = logging.getLogger(__name__)

class ApprovalAgent:
    def __init__(self):
        pass

    async def approval_routing_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Determines who needs to approve the invoice and sends notifications.
        Transitions state to AWAITING_APPROVAL.
        """
        invoice_id = state.get("invoice_id")
        company_id = state.get("company_id")
        
        # If explicitly already needing approval (e.g. from Validation variance)
        # We still need to determine WHO approves.
        
        try:
            invoice = await db.invoices.get_by_field("invoice_id", invoice_id)
            if not invoice or not invoice.data:
                state["errors"] = ["Invoice missing"]
                return state
                
            data: InvoiceData = InvoiceData(**invoice.data.model_dump())
            amount = data.total
            
            # 1. Fetch Matrix
            config = await db.config.get_by_field("company_id", company_id)
            if not config:
                logger.warning("No config found, routing to default admin")
                approvers = ["admin"]
            else:
                approvers = self._determine_approvers(amount, config.approval_matrix.rules)
            
            # 2. SoD Check (Mock: ensure creator != approver)
            # In real system, we'd check audit logs for who uploaded/created
            # creator = ...
            # if creator in approvers: remove/flag
            
            if not approvers:
                # No approvers needed? Auto-approve?
                # If we are here, likely we NEED approval due to flow logic
                # Default to fallback config or admin
                approvers = ["finance_manager"]

            logger.info(f"Invoice {invoice_id} routed to: {approvers}")

            # 3. Notify
            await notification_tool.send_notification(
                approvers, 
                f"Approval Needed: Invoice {invoice_id}",
                f"Please approve invoice for {data.vendor_name} amount {data.total}"
            )
            
            # 4. Update State
            # We don't change 'status' here if it's already AWAITING_APPROVAL or passed in to become so.
            # But the node responsibility is to ensure it IS awaiting approval.
            await db.invoices.update(invoice_id, {
                "status": InvoiceStatus.AWAITING_APPROVAL,
                "human_approval_required": True
                # Store assigned_approvers in DB ideally
            })
            
            state["current_state"] = InvoiceStatus.AWAITING_APPROVAL
            state["human_approval_required"] = True
            
        except Exception as e:
            logger.error(f"Approval routing failed: {e}")
            state["errors"] = [str(e)]
            state["current_state"] = InvoiceStatus.EXCEPTION

        return state

    def _determine_approvers(self, amount: float, rules: List[ApprovalRule]) -> List[str]:
        """
        Matches amount against rules to find approvers.
        """
        required = set()
        for rule in rules:
            # Check min
            if amount >= rule.amount_min:
                # Check max (if None, it's infinity)
                if rule.amount_max is None or amount <= rule.amount_max:
                    if rule.specific_approvers:
                        required.update(rule.specific_approvers)
                    elif rule.required_role:
                        # In real app, look up users by role
                        required.add(f"role:{rule.required_role}")
        
        return list(required)

approval_agent = ApprovalAgent()
