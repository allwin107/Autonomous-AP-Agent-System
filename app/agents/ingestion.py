import asyncio
import logging
import uuid
from datetime import datetime
from typing import List, Dict, Any

from app.database import db
from app.tools.gmail_tool import gmail_tool
from app.models.invoice import Invoice, InvoiceState, InvoiceStatus

logger = logging.getLogger(__name__)

class IngestionAgent:
    def __init__(self):
        self.is_running = False

    async def start_polling(self, interval_seconds: int = 300):
        """Start the background polling loop."""
        self.is_running = True
        logger.info("Starting Ingestion Agent polling loop...")
        while self.is_running:
            try:
                await self.process_inbox()
            except Exception as e:
                logger.error(f"Error in ingestion polling: {e}")
            
            await asyncio.sleep(interval_seconds)

    async def stop(self):
        self.is_running = False

    async def process_inbox(self):
        """Check inbox for new invoices and process them."""
        logger.info("Checking inbox for new invoices...")
        messages = gmail_tool.fetch_unread_invoices() # Pass query if needed, default is fine
        
        for msg in messages:
            try:
                message_id = msg['id']
                subject = "Unknown Subject" # Simplify for now, need parsing logic to get subject from 'payload' headers
                
                # Extract headers for better logging
                headers = msg.get('payload', {}).get('headers', [])
                for h in headers:
                    if h['name'] == 'Subject':
                        subject = h['value']

                print(f"Processing email: {subject} ({message_id})")
                
                attachments = gmail_tool.extract_attachments(message_id)
                if not attachments:
                    print(f"No attachments found in {message_id}, skipping.")
                    continue

                for att in attachments:
                    # Only process likely invoice types
                    if att['mimeType'] not in ['application/pdf', 'image/jpeg', 'image/png']:
                        continue
                        
                    # 1. Store file in GridFS
                    file_id = await db.fs.upload_from_stream(
                        att['filename'], 
                        att['data'],
                        metadata={"source": "gmail", "message_id": message_id}
                    )
                    
                    # 2. Create Invoice Record
                    invoice_id = f"INV-{uuid.uuid4().hex[:8].upper()}"
                    new_invoice = Invoice(
                        invoice_id=invoice_id,
                        company_id="acme_corp", # Default for now, could infer from email recipient
                        status=InvoiceStatus.INGESTION,
                        raw_text="", # To be filled by extraction
                        file_path=str(file_id),
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    
                    await db.invoices.create(new_invoice)
                    
                    # 3. Log Audit
                    await db.audit.log_action(
                        company_id="acme_corp",
                        actor={"id": "agent-ingestion", "name": "Ingestion Agent", "type": "AGENT"},
                        action_type="SYSTEM_EVENT",
                        details=f"Ingested invoice {att['filename']} from email {message_id}",
                        invoice_id=invoice_id
                    )
                    
                    print(f"Ingested invoice {invoice_id} from {att['filename']}")

                # 4. Mark as read
                gmail_tool.mark_as_read(message_id)

            except Exception as e:
                logger.error(f"Failed to process message {msg.get('id')}: {e}")

    async def ingestion_node(self, state: InvoiceState) -> InvoiceState:
        """
        LangGraph node for ingestion. 
        This might be used if the flow expects to trigger ingestion explicitly, 
        or passes an already ingested invoice ID to start the flow.
        
        If this node is the START of a flow, it might just retrieve the invoice 
        from DB based on ID passed in state.
        """
        invoice_id = state.get("invoice_id")
        if not invoice_id:
            return state # Or raise error
            
        invoice = await db.invoices.get_by_field("invoice_id", invoice_id)
        if invoice:
             state["current_state"] = InvoiceStatus.EXTRACTION
             # Could load more data into state here
        
        return state

ingestion_agent = IngestionAgent()
