from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Body
from pydantic import BaseModel

from app.database import db
from app.api.auth import get_current_active_user, get_admin_user, User
from app.models.invoice import Invoice, InvoiceStatus, ValidationResults
from app.workflow.graph import invoice_workflow
from app.workflow.state import InvoiceState
from app.guardrails.permissions import Permission
from app.guardrails.permissions import Permission
from app.guardrails.decorators import require_permission, enforce_sod
from app.agents.po_creator import po_creator

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
@enforce_sod(action="approve")
async def approve_invoice(
    invoice_id: str, 
    decision: ApprovalDecision = Body(...),
    current_user: User = Depends(require_permission(Permission.APPROVE_INVOICE))
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

    # Check for Non-PO Approval -> Create Retrospective PO
    if invoice.matching and invoice.matching.match_status == "NON_PO_APPROVAL_NEEDED":
        await po_creator.create_retrospective_po(
            invoice_id, 
            invoice.company_id, 
            approved_by=current_user.username
        )

    # Move State
    new_status = InvoiceStatus.PAYMENT_PREPARATION
    await db.invoices.update(invoice_id, {"status": new_status})
    
    # TODO: Resume workflow if needed, or if we just manually stepped it forward
    
    return {"message": "Invoice Approved", "invoice_status": new_status}

@router.post("/{invoice_id}/reject", response_model=ApprovalResponse)
@enforce_sod(action="reject") # SoD might be less strict for rejection, but good policy
async def reject_invoice(
    invoice_id: str, 
    decision: ApprovalDecision = Body(...),
    current_user: User = Depends(require_permission(Permission.REJECT_INVOICE))
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
    

from fastapi.responses import HTMLResponse

@router.get("/ui/{invoice_id}", response_class=HTMLResponse)
async def get_approval_ui(invoice_id: str):
    """Simple notification landing page for approvers."""
    invoice = await db.invoices.get_by_field("invoice_id", invoice_id)
    if not invoice:
        return "<h1>Invoice not found</h1>"
        
    return f"""
    <html>
        <head><title>Approve Invoice {invoice_id}</title></head>
        <body style="font-family: sans-serif; padding: 20px;">
            <h1>Approval Request</h1>
            <p><strong>Invoice ID:</strong> {invoice.invoice_id}</p>
            <p><strong>Vendor:</strong> {invoice.data.vendor_name if invoice.data else 'N/A'}</p>
            <p><strong>Amount:</strong> {invoice.data.total if invoice.data else 'N/A'}</p>
            <p><strong>Status:</strong> {invoice.status}</p>
            <hr/>
            <form action="/api/approvals/{invoice_id}/approve" method="post">
                <textarea name="comments" placeholder="Comments"></textarea><br/>
                <button type="submit" style="background:green; color:white; padding:10px;">Approve</button>
            </form>
            <form action="/api/approvals/{invoice_id}/reject" method="post">
                <textarea name="comments" placeholder="Reason"></textarea><br/>
                <button type="submit" style="background:red; color:white; padding:10px;">Reject</button>
            </form>
        </body>
    </html>
    """
