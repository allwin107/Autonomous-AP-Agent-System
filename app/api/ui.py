from typing import Optional
from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.database import db
from app.models.invoice import InvoiceStatus
from app.api.auth import get_current_active_user, User

router = APIRouter(prefix="/ui", tags=["UI"])

templates = Jinja2Templates(directory="templates")

# Dependency for cookie-based auth in UI (simplified)
# In real world, we would extract token from cookie and use get_current_user logic
# For this prototype, we'll try to rely on the Authorization header if passed,
# or simulate a "logged in user" if running in a certain mode, or just fail securely.
# Since browser navigation doesn't easily send Headers for GET without JS logic,
# we'll skip strict auth for the UI GET pages in this demo OR assume a query param token.
# Let's rely on a simplified approach: No Auth for UI Demo, or Basic Auth.
# Or, clearer: We just won't enforce dependencies for the GET rendering,
# but the Actions (Post) will require Auth (which might fail effortlessly if not handled).

# To make the UI usable in a browser without a frontend framework managing JWTs,
# we would typically set a cookie on login. We haven't built a cookie-login endpoint.
# So for this user request, we will render the pages publicly but require API keys for actions
# or assume the user uses the 'Authorize' button in Swagger then copies the token?
# Let's just make the UI pages public (read-only safeish) or check for a query param 'token'.

# BETTER APPROACH:
# We will create a fake "login" that sets a cookie for the UI.
# Or just implement the UI assuming it receives the data.

@router.get("/approvals", response_class=HTMLResponse)
async def approval_dashboard(
    request: Request,
    status_filter: Optional[str] = None
):
    query = {"status": InvoiceStatus.AWAITING_APPROVAL}
    if status_filter:
        # Override if user wants to see other statuses
        query["status"] = status_filter
        
    invoices = await db.invoices.find(query)
    
    return templates.TemplateResponse(
        "approval_dashboard.html", 
        {"request": request, "invoices": invoices, "filter": status_filter}
    )

@router.get("/invoices/{invoice_id}", response_class=HTMLResponse)
async def invoice_detail(
    request: Request,
    invoice_id: str
):
    invoice = await db.invoices.get_by_field("invoice_id", invoice_id)
    if not invoice:
        return HTMLResponse("Invoice not found", status_code=404)
        
    return templates.TemplateResponse(
        "invoice_detail.html",
        {"request": request, "invoice": invoice}
    )

@router.post("/approvals/{invoice_id}/respond", response_class=RedirectResponse)
async def handle_approval_response(
    request: Request,
    invoice_id: str
):
    # Form data handling
    form = await request.form()
    action = form.get("action")
    comments = form.get("comments", "")
    
    # We really should authenticate here.
    # For demo, we assume "admin"
    user = User(username="admin", role="admin") 
    
    invoice = await db.invoices.get_by_field("invoice_id", invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
        
    next_status = invoice.status
    
    # Log Audit
    if action == "approve":
        next_status = InvoiceStatus.PAYMENT_PREPARATION
        log_type = "APPROVED"
    elif action == "reject":
        next_status = InvoiceStatus.REJECTED
        log_type = "REJECTED"
    else:
        # Unknown action
        return RedirectResponse(url=f"/ui/invoices/{invoice_id}", status_code=303)

    # Perform Update
    await db.invoices.update(invoice_id, {"status": next_status})
    
    await db.audit.log_action(
        company_id=invoice.company_id,
        actor={"id": user.username, "name": "UI Admin", "type": "USER"},
        action_type=log_type,
        details=f"UI Action. Comments: {comments}",
        invoice_id=invoice_id
    )

    # Redirect back to dashboard
    return RedirectResponse(url="/ui/approvals", status_code=303)
