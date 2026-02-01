import logging
import json
import io
from typing import Dict, Any, Optional
from datetime import datetime

from app.database import db
from app.models.invoice import Invoice, InvoiceStatus, InvoiceData, ValidationResults
from app.tools.ocr_tool import ocr_tool
from app.tools.groq_llm import groq_tool

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT_TEMPLATE = """
You are an expert invoice data extractor. 
Analyze the following invoice text (extracted via OCR) and extract key information into a strict JSON format matching the schema below.

Text from Invoice:
{invoice_text}

Required Output Schema (JSON):
{{
    "vendor_name": "string",
    "vendor_id": "string (optional, null if unknown)",
    "invoice_number": "string",
    "invoice_date": "YYYY-MM-DD",
    "due_date": "YYYY-MM-DD (optional)",
    "line_items": [
        {{
            "item_id": 1,
            "description": "string",
            "quantity": float,
            "unit_price": float,
            "line_total": float,
            "gl_code": "string (optional)",
            "category": "string (optional)"
        }}
    ],
    "subtotal": float,
    "vat_rate": float (e.g. 0.20 for 20%),
    "vat_amount": float,
    "total": float,
    "currency": "string (e.g. GBP, USD)",
    "po_reference": "string (optional)"
}}

Instructions:
1. Return ONLY valid JSON.
2. If a field is missing, use null (or 0.0 for numbers).
3. Dates must be ISO 8601 format.
4. Assume currency is GBP unless specified otherwise.
"""

class ExtractionAgent:
    def __init__(self):
        pass

    async def extraction_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Refined Node for LangGraph.
        """
        invoice_id = state.get("invoice_id")
        if not invoice_id:
            logger.error("No invoice_id in state")
            state["errors"] = ["Missing invoice_id"]
            return state

        try:
            # 1. Fetch Invoice
            invoice = await db.invoices.get_by_field("invoice_id", invoice_id)
            if not invoice:
                logger.error(f"Invoice {invoice_id} not found")
                state["errors"] = [f"Invoice {invoice_id} not found"]
                return state

            if invoice.status == InvoiceStatus.EXTRACTION:
                 # Already processing? 
                 pass

            # Update status
            await db.invoices.update(invoice_id, {"status": InvoiceStatus.EXTRACTION, "previous_state": invoice.status})

            # 2. Get File Content
            # Assuming file_path stores GridFS ID
            if not invoice.file_path:
                 logger.error(f"No file path for invoice {invoice_id}")
                 state["errors"] = ["No file attached"]
                 return state

            file_id = invoice.file_path
            
            # Download from GridFS
            try:
                from bson import ObjectId
                grid_out = await db.fs.open_download_stream(ObjectId(file_id))
                content = await grid_out.read()
                filename = grid_out.filename
            except Exception as e:
                 logger.error(f"GridFS retrieval failed: {e}")
                 state["errors"] = [f"File retrieval failed: {e}"]
                 return state

            mime_type = "application/pdf" if filename.lower().endswith(".pdf") else "image/png" # Simple inference

            # 3. Perform OCR
            raw_text = ocr_tool.extract_text(content, mime_type)
            if not raw_text or len(raw_text.strip()) < 10:
                logger.warning(f"OCR yielded no text for {invoice_id}")
                # Could flag as manual review needed
                state["errors"] = ["OCR Extracted Empty Text"]
                await db.invoices.update(invoice_id, {"status": InvoiceStatus.EXCEPTION})
                return state

            # Store raw text
            await db.invoices.update(invoice_id, {"raw_text": raw_text})

            # 4. LLM Extraction
            prompt = EXTRACTION_PROMPT_TEMPLATE.format(invoice_text=raw_text[:10000]) # Truncate if too long
            extracted_json = groq_tool.generate_structured(prompt)
            
            # 5. Map to Model
            try:
                # Sanitize / Validate with Pydantic
                invoice_data = InvoiceData(**extracted_json)
                
                # Recalculate totals check
                calc_total = invoice_data.calculate_totals()
                
                # Update Invoice
                await db.invoices.update(invoice_id, {
                    "data": invoice_data.dict(),
                    "status": InvoiceStatus.VALIDATION # Move to next stage
                })
                
                # Update State
                state["invoice_data"] = invoice_data.model_dump()
                state["current_state"] = InvoiceStatus.VALIDATION
                
                logger.info(f"Extraction successful for {invoice_id}")

            except Exception as e:
                logger.error(f"Validation of extracted data failed: {e}")
                state["errors"] = [f"Data validation failed: {e}"]
                # Flag for manual review?
                await db.invoices.update(invoice_id, {"status": InvoiceStatus.EXCEPTION})

        except Exception as e:
            logger.error(f"Extraction process failed: {e}")
            state["errors"] = [str(e)]
            
        return state

extraction_agent = ExtractionAgent()
