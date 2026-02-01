import sys
import os
sys.path.append(os.getcwd())
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.agents.extraction import ExtractionAgent
from app.models.invoice import Invoice, InvoiceStatus

@pytest.mark.asyncio
async def test_extraction_node_success():
    # Mock DB
    with patch("app.agents.extraction.db") as mock_db:
        # Mock Invoices
        mock_invoice = MagicMock()
        mock_invoice.invoice_id = "inv_123"
        mock_invoice.company_id = "acme"
        mock_invoice.status = InvoiceStatus.INGESTION
        mock_invoice.file_path = "000000000000000000000123"
        
        mock_db.invoices.get_by_field = AsyncMock(return_value=mock_invoice)
        mock_db.invoices.update = AsyncMock()
        
        # Mock GridFS
        mock_grid_out = AsyncMock()
        mock_grid_out.read.return_value = b"fake_content"
        mock_grid_out.filename = "invoice.pdf"
        mock_db.fs.open_download_stream = AsyncMock(return_value=mock_grid_out)

        # Mock OCR Tool
        with patch("app.agents.extraction.ocr_tool") as mock_ocr:
            mock_ocr.extract_text.return_value = "Invoice #123 Total: 100.00"

            # Mock Groq Tool
            with patch("app.agents.extraction.groq_tool") as mock_groq:
                mock_groq.generate_structured.return_value = {
                    "vendor_name": "Test Vendor",
                    "invoice_number": "123",
                    "invoice_date": "2024-01-01",
                    "total": 100.00,
                    "subtotal": 100.00,
                    "vat_amount": 0.0,
                    "line_items": []
                }
                
                agent = ExtractionAgent()
                state = {"invoice_id": "inv_123"}
                
                result_state = await agent.extraction_node(state)
                
                # Verify DB calls
                # 1. Get invoice
                mock_db.invoices.get_by_field.assert_called_with("invoice_id", "inv_123")
                # 2. Update status to EXTRACTION
                # 3. Update raw text
                # 4. Update status to VALIDATION with data
                assert mock_db.invoices.update.call_count >= 3
                
                # Verify Logic
                assert "invoice_data" in result_state
                assert result_state["invoice_data"]["vendor_name"] == "Test Vendor"
                assert result_state["current_state"] == InvoiceStatus.VALIDATION

@pytest.mark.asyncio
async def test_extraction_node_ocr_failure():
    with patch("app.agents.extraction.db") as mock_db:
        mock_invoice = MagicMock()
        mock_invoice.file_path = "000000000000000000000123"
        mock_db.invoices.get_by_field = AsyncMock(return_value=mock_invoice)
        mock_db.invoices.update = AsyncMock()
        
        mock_grid_out = AsyncMock()
        mock_grid_out.read.return_value = b"empty"
        mock_grid_out.filename = "invoice.pdf"
        mock_db.fs.open_download_stream = AsyncMock(return_value=mock_grid_out)
        
        with patch("app.agents.extraction.ocr_tool") as mock_ocr:
            mock_ocr.extract_text.return_value = "" # Empty text
            
            agent = ExtractionAgent()
            state = {"invoice_id": "inv_123"}
            result_state = await agent.extraction_node(state)
            
            assert "OCR Extracted Empty Text" in result_state["errors"]
