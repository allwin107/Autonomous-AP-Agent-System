import logging
import uuid
from datetime import datetime
from typing import Optional

from app.database import db
from app.models.invoice import InvoiceData, LineItem
from app.models.purchase_order import PurchaseOrder, POStatus

logger = logging.getLogger(__name__)

class POCreator:
    def __init__(self):
        pass

    async def create_retrospective_po(self, invoice_id: str, company_id: str, approved_by: str) -> Optional[PurchaseOrder]:
        """
        Creates a PO based on an approved invoice.
        """
        invoice = await db.invoices.get_by_field("invoice_id", invoice_id)
        if not invoice or not invoice.data:
            logger.error(f"Cannot create PO for {invoice_id}: Data missing")
            return None

        data: InvoiceData = InvoiceData(**invoice.data.model_dump())
        
        # Generate PO Number
        po_number = f"PO-RETRO-{uuid.uuid4().hex[:6].upper()}"
        
        # Create PO Items from Invoice Items
        po_items = []
        for item in data.line_items:
            po_items.append(LineItem(
                item_id=item.item_id, # Keep original type (int)
                description=item.description,
                quantity=item.quantity,
                unit_price=item.unit_price,
                line_total=item.line_total
            ))
            
        po = PurchaseOrder(
            po_number=po_number,
            company_id=company_id,
            vendor_id=data.vendor_id or "unknown",
            vendor_name=data.vendor_name or "Unknown Vendor",
            requester_email=f"{approved_by}@example.com", # Placeholder
            department="Finance", # Placeholder
            status=POStatus.ISSUED,
            created_at=datetime.utcnow(),
            po_date=datetime.utcnow(),
            total=data.total,
            subtotal=data.total, # Assuming no VAT or VAT included? Better to use net if available
            vat_amount=data.vat_amount,
            currency=data.currency,
            line_items=po_items,
            metadata={
                "created_from_invoice": invoice_id,
                "type": "RETROSPECTIVE",
                "approved_by": approved_by
            }
        )
        
        # Save PO
        await db.db["purchase_orders"].insert_one(po.model_dump())
        logger.info(f"Created Retrospective PO {po_number} for Invoice {invoice_id}")
        
        # Link PO to Invoice
        await db.invoices.update(invoice_id, {
            "data.po_reference": po_number,
            "matching.has_po": True,
            "matching.match_status": "RETRO_PO_CREATED"
        })
        
        return po

po_creator = POCreator()
