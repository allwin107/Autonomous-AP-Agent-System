import pytest
import os
import sys
sys.path.append(os.getcwd())
from unittest.mock import AsyncMock, patch, MagicMock
from app.agents.ingestion import IngestionAgent
from app.models.invoice import InvoiceStatus

@pytest.mark.asyncio
async def test_scenario_1_email_ingestion(mock_db):
    """
    Scenario 1: Receipt of an invoice via email.
    """
    agent = IngestionAgent()
    
    # 1. Mock Gmail Tool
    with patch("app.agents.ingestion.gmail_tool") as mock_gmail:
        mock_gmail.fetch_unread_invoices.return_value = [
            {
                "id": "msg-123",
                "payload": {"headers": [{"name": "Subject", "value": "Invoice INV-999"}]}
            }
        ]
        mock_gmail.extract_attachments.return_value = [
            {"filename": "inv_999.pdf", "data": b"fake_pdf_content", "mimeType": "application/pdf"}
        ]
        
        # 2. Mock storage (GridFS) locally in integration
        with patch("app.agents.ingestion.db") as mock_db_local:
            mock_db_local.fs.upload_from_stream = AsyncMock(return_value="grid-file-id")
            mock_db_local.invoices = mock_db.invoices
            mock_db_local.audit = mock_db.audit
            
            # 3. Trigger ingestion
            await agent.process_inbox()
            
            # 4. Assertions
            mock_db.invoices.create.assert_called_once()
            created_invoice = mock_db.invoices.create.call_args[0][0]
            assert created_invoice.status == InvoiceStatus.INGESTION
            assert created_invoice.file_path == "grid-file-id"
