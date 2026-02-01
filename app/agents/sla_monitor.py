import logging
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any
from app.database import db
from app.models.invoice import Invoice, InvoiceStatus
from app.tools.notification_tool import notification_tool

logger = logging.getLogger(__name__)

class SLAMonitor:
    """
    Background monitor for payment deadlines and approval SLAs.
    """
    
    async def check_payment_deadlines(self):
        """
        Calculates days until payment due and updates urgency.
        """
        now = datetime.utcnow()
        # Find all unpaid/unrejected invoices
        query = {
            "status": {"$notin": [InvoiceStatus.PAID, InvoiceStatus.REJECTED]}
        }
        invoices_data = await db.db["invoices"].find(query).to_list(None)
        
        for doc in invoices_data:
            invoice = Invoice(**doc)
            if not invoice.data or not invoice.data.due_date:
                continue
                
            diff = invoice.data.due_date - now
            days = diff.total_seconds() / (24 * 3600)
            hours = diff.total_seconds() / 3600
            
            new_urgency = "NORMAL"
            if hours < 24:
                new_urgency = "CRITICAL"
            elif days < 3:
                new_urgency = "URGENT"
            elif days < 7:
                new_urgency = "WARNING"
            
            if new_urgency != invoice.urgency:
                await self.escalate_invoice(
                    invoice.invoice_id, 
                    reason=f"Payment deadline approaching ({days:.1f} days remaining)", 
                    urgency=new_urgency
                )

    async def check_approval_slas(self, sla_hours: int = 48):
        """
        Monitors invoices pending approval.
        """
        now = datetime.utcnow()
        query = {
            "status": InvoiceStatus.AWAITING_APPROVAL
        }
        pending_invoices = await db.db["invoices"].find(query).to_list(None)
        
        for doc in pending_invoices:
            invoice = Invoice(**doc)
            pending_since = invoice.updated_at
            waited_hours = (now - pending_since).total_seconds() / 3600
            
            if waited_hours > sla_hours:
                # Breach!
                if invoice.sla_status != "BREACHED":
                    await self.escalate_invoice(
                        invoice.invoice_id,
                        reason=f"Approval SLA breached ({waited_hours:.1f}h / {sla_hours}h)",
                        urgency="CRITICAL"
                    )
                    await db.invoices.update(invoice.invoice_id, {"sla_status": "BREACHED"})
            elif waited_hours > (sla_hours * 0.75):
                # At Risk
                if invoice.sla_status == "COMPLIANT":
                    await db.invoices.update(invoice.invoice_id, {"sla_status": "AT_RISK"})
                    logger.info(f"Invoice {invoice.invoice_id} is AT RISK for SLA breach.")

    async def escalate_invoice(self, invoice_id: str, reason: str, urgency: str):
        """
        Updates invoice urgency and sends notifications.
        """
        logger.warning(f"Escalating {invoice_id} to {urgency}. Reason: {reason}")
        
        # Update Invoice
        escalation_entry = {
            "urgency": urgency,
            "reason": reason,
            "timestamp": datetime.utcnow()
        }
        
        await db.db["invoices"].update_one(
            {"invoice_id": invoice_id},
            {
                "$set": {"urgency": urgency},
                "$push": {"escalation_history": escalation_entry}
            }
        )
        
        # Determine recipients
        recipients = ["finance_team@company.com"] # Default
        if urgency == "CRITICAL":
            recipients.append("cfo@company.com")
        elif urgency == "URGENT":
            recipients.append("ap_manager@company.com")
            
        # Send notifications
        subject = f"[{urgency}] SLA Escalation: Invoice {invoice_id}"
        message = f"URGENT ACTION REQUIRED: {reason}. Status updated to {urgency}."
        
        # Slack @mention for urgent/critical
        if urgency in ["URGENT", "CRITICAL"]:
            await notification_tool.send_notification(
                users=recipients,
                subject=subject,
                message=message,
                channels=["email", "slack"]
            )
        else:
            await notification_tool.send_notification(
                users=recipients,
                subject=subject,
                message=message,
                channels=["email"]
            )

    async def run_metrics(self) -> Dict[str, Any]:
        """
        Calculates SLA compliance metrics.
        """
        # In a real app, this would use aggregation framework
        invoices = await db.db["invoices"].find({}).to_list(None)
        total = len(invoices)
        if total == 0:
            return {"compliance_rate": 1.0}
            
        on_time = sum(1 for inv in invoices if inv.get("sla_status") == "COMPLIANT")
        breached = sum(1 for inv in invoices if inv.get("sla_status") == "BREACHED")
        
        return {
            "total_invoices": total,
            "on_time_count": on_time,
            "breached_count": breached,
            "compliance_rate": on_time / total,
            "urgency_distribution": {
                "CRITICAL": sum(1 for inv in invoices if inv.get("urgency") == "CRITICAL"),
                "URGENT": sum(1 for inv in invoices if inv.get("urgency") == "URGENT"),
                "WARNING": sum(1 for inv in invoices if inv.get("urgency") == "WARNING"),
                "NORMAL": sum(1 for inv in invoices if inv.get("urgency") == "NORMAL"),
            }
        }

sla_monitor = SLAMonitor()
