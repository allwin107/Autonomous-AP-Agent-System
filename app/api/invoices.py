import uuid
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Depends, Query
from pydantic import BaseModel

from app.database import db
from app.api.auth import get_current_active_user, User
from app.models.invoice import Invoice, InvoiceStatus
from app.workflow.graph import invoice_workflow
from app.workflow.state import InvoiceState

router = APIRouter(prefix="/api/invoices", tags=["Invoices"])

# Request Models
class RetryRequest(BaseModel):
    reason: Optional[str] = None

# Background Task
async def trigger_workflow(invoice_id: str):
    app = invoice_workflow.get_runnable()
    initial_state = InvoiceState(
        invoice_id=invoice_id,
        company_id="acme_corp", # TODO: Get from context/auth
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
    config = {"configurable": {"thread_id": invoice_id}}
    # Fire and forget (or await if simple)
    # Using ainvoke in background ensures it runs without blocking API
    await app.ainvoke(initial_state, config=config)

# Helper for GridFS upload details
async def upload_to_gridfs(file: UploadFile, company_id: str) -> str:
    from bson import ObjectId
    try:
        file_id = await db.fs.upload_from_stream(
            file.filename,
            file.file,
            metadata={"source": "manual_upload", "company_id": company_id}
        )
        return str(file_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")

@router.post("/upload", response_model=Invoice, status_code=201)
async def upload_invoice(
    file: UploadFile = File(...), 
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(get_current_active_user)
):
    if file.content_type not in ["application/pdf", "image/png", "image/jpeg"]:
        raise HTTPException(status_code=400, detail="Invalid file type. Only PDF, PNG, JPEG allowd.")

    invoice_id = f"INV-{uuid.uuid4().hex[:8].upper()}"
    file_id = await upload_to_gridfs(file, "acme_corp")

    new_invoice = Invoice(
        invoice_id=invoice_id,
        company_id="acme_corp", # TODO: Dynamic company
        status=InvoiceStatus.INGESTION,
        file_path=file_id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    await db.invoices.create(new_invoice)
    
    # Trigger Workflow
    background_tasks.add_task(trigger_workflow, invoice_id)
    
    return new_invoice

@router.get("/", response_model=List[Invoice])
async def list_invoices(
    status: Optional[InvoiceStatus] = None,
    vendor_name: Optional[str] = None,
    limit: int = 50,
    skip: int = 0,
    current_user: User = Depends(get_current_active_user)
):
    query = {}
    if status:
        query["status"] = status
    if vendor_name:
        query["data.vendor_name"] = {"$regex": vendor_name, "$options": "i"}

    # TODO: Implement complex filtering in Repo or directly here mock for now
    # Using find without complex pagination logic for MVP
    invoices = await db.invoices.find(query) # Repositories usually handle skip/limit
    return invoices[skip: skip+limit]

@router.get("/{invoice_id}", response_model=Invoice)
async def get_invoice(invoice_id: str, current_user: User = Depends(get_current_active_user)):
    invoice = await db.invoices.get_by_field("invoice_id", invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice

@router.put("/{invoice_id}/retry", response_model=Invoice)
async def retry_invoice(
    invoice_id: str, 
    retry_data: RetryRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user)
):
    invoice = await db.invoices.get_by_field("invoice_id", invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
        
    if invoice.status not in [InvoiceStatus.EXCEPTION, InvoiceStatus.REJECTED]:
         raise HTTPException(status_code=400, detail="Only failed invoices can be retried")

    # update status
    await db.invoices.update(invoice_id, {
        "status": InvoiceStatus.INGESTION, 
        "retry_count": invoice.retry_count + 1,
        "previous_state": invoice.status
    })
    
    # Trigger workflow
    background_tasks.add_task(trigger_workflow, invoice_id)
    
    # Return updated (fetching fresh)
    return await db.invoices.get_by_field("invoice_id", invoice_id)
