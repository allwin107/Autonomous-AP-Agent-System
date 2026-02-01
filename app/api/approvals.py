from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Body
from pydantic import BaseModel

from app.database import db
from app.api.auth import get_current_active_user, get_admin_user, User
from app.models.invoice import Invoice, InvoiceStatus, ValidationResults
from app.workflow.graph import invoice_workflow
from app.workflow.state import InvoiceState

router = APIRouter(prefix="/api/approvals", tags=["Approvals"])

class ApprovalDecision(BaseModel):
    approved: bool
    comments: Optional[str] = None

class ApprovalResponse(BaseModel):
    message: str
    invoice_status: str

# Helper to resume workflow
async def resume_workflow_approval(invoice_id: str, approved: bool, comments: str):
    app = invoice_workflow.get_runnable()
    
    # We need to update the state to reflect decision, then resume
    # LangGraph MemorySaver allows us to update state
    config = {"configurable": {"thread_id": invoice_id}}
    
    # Get current state to verify?
    # For now, simplistic approach: update the state with resume signal
    # Since we paused at 'approval' node (or rather, the edge conditional routed to END or AWAITING).
    # If using 'interrupt_before', we would just 'invoke(None)'. 
    # But here we likely ended the flow. So we restart with new state from where we left off?
    # Or more robustly: The workflow state has 'current_state' = AWAITING_APPROVAL.
    # We change it to PAYMENT or EXCEPTION and run again.
    
    new_status = InvoiceStatus.PAYMENT_SCHEDULED if approved else InvoiceStatus.REJECTED
    
    # Update state manually in memory (checkpoint) logic
    # app.update_state(config, {"current_state": new_status, "human_approval_required": False})
    # app.invoke(None, config)
    
    # Since we might not have persistent checkpointing logic fully setup with DB yet (using InMemory),
    # verifying 'resume' is tricky across process restarts.
    # For this MVP API, we will just update DB and trigger a new run starting from the 'approval' equivalent step
    # OR we treat this as a manual status update that mimics the workflow result.
    
    pass

@router.get("/pending", response_model=List[Invoice])
async def list_pending_approvals(current_user: User = Depends(get_current_active_user)):
    # Filter for AWAITING_APPROVAL
    # In real world, filter by user/role permissions too
    return await db.invoices.find({"status": InvoiceStatus.AWAITING_APPROVAL})

@router.post("/{invoice_id}/approve", response_model=ApprovalResponse)
async def approve_invoice(
    invoice_id: str, 
    decision: ApprovalDecision = Body(...),
    current_user: User = Depends(get_admin_user) # Only admins for now
):
    invoice = await db.invoices.get_by_field("invoice_id", invoice_id)
    if not invoice or invoice.status != InvoiceStatus.AWAITING_APPROVAL:
        raise HTTPException(status_code=400, detail="Invoice not awaiting approval")

    # Log action
    await db.audit.log_action(
        company_id=invoice.company_id,
        actor={"id": current_user.username, "name": current_user.full_name, "type": "USER"},
        action_type="APPROVED",
        details=f"Comments: {decision.comments}",
        invoice_id=invoice_id
    )

    # Move State
    new_status = InvoiceStatus.PAYMENT_PREPARATION
    await db.invoices.update(invoice_id, {"status": new_status})
    
    # TODO: Resume workflow if needed, or if we just manually stepped it forward
    
    return {"message": "Invoice Approved", "invoice_status": new_status}

@router.post("/{invoice_id}/reject", response_model=ApprovalResponse)
async def reject_invoice(
    invoice_id: str, 
    decision: ApprovalDecision = Body(...),
    current_user: User = Depends(get_admin_user)
):
    invoice = await db.invoices.get_by_field("invoice_id", invoice_id)
    if not invoice or invoice.status != InvoiceStatus.AWAITING_APPROVAL:
        raise HTTPException(status_code=400, detail="Invoice not awaiting approval")

    # Log action
    await db.audit.log_action(
        company_id=invoice.company_id,
        actor={"id": current_user.username, "name": current_user.full_name, "type": "USER"},
        action_type="REJECTED",
        details=f"Reason: {decision.comments}",
        invoice_id=invoice_id
    )

    # Move State
    new_status = InvoiceStatus.REJECTED
    await db.invoices.update(invoice_id, {"status": new_status})
    
    return {"message": "Invoice Rejected", "invoice_status": new_status}
