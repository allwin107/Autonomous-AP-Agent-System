import sys
import os
sys.path.append(os.getcwd())
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from app.agents.ingestion import IngestionAgent
from app.models.invoice import InvoiceStatus

@pytest.mark.asyncio
async def test_process_inbox_with_attachments():
    # Mock GmailTool
    with patch("app.agents.ingestion.gmail_tool") as mock_gmail:
        # 1. Setup mock emails
        mock_gmail.fetch_unread_invoices.return_value = [
            {'id': 'msg_1', 'payload': {'headers': [{'name': 'Subject', 'value': 'Invoice 123'}]}}
        ]
        
        # 2. Setup mock attachments
        mock_gmail.extract_attachments.return_value = [
            {'filename': 'invoice.pdf', 'mimeType': 'application/pdf', 'data': b'%PDF-1.4...'}
        ]
        
        # Mock Database
        with patch("app.agents.ingestion.db") as mock_db:
            mock_db.fs = AsyncMock()
            mock_db.fs.upload_from_stream.return_value = "file_id_123"
            
            mock_db.invoices = AsyncMock()
            mock_db.invoices.create = AsyncMock()
            
            mock_db.audit = AsyncMock()
            mock_db.audit.log_action = AsyncMock()
            
            # Run the agent
            agent = IngestionAgent()
            await agent.process_inbox()
            
            # Add assertions
            # Verify Gmail interactions
            mock_gmail.fetch_unread_invoices.assert_called_once()
            mock_gmail.extract_attachments.assert_called_with('msg_1')
            mock_gmail.mark_as_read.assert_called_with('msg_1')
            
            # Verify DB operations
            mock_db.fs.upload_from_stream.assert_called_once()
            mock_db.invoices.create.assert_called_once()
            
            # Check created invoice status
            created_invoice = mock_db.invoices.create.call_args[0][0]
            assert created_invoice.status == InvoiceStatus.INGESTION
            assert created_invoice.company_id == "acme_corp"
            assert created_invoice.file_path == "file_id_123"

@pytest.mark.asyncio
async def test_process_inbox_no_attachments():
    with patch("app.agents.ingestion.gmail_tool") as mock_gmail:
        mock_gmail.fetch_unread_invoices.return_value = [{'id': 'msg_2'}]
        mock_gmail.extract_attachments.return_value = []
        
        with patch("app.agents.ingestion.db") as mock_db:
             agent = IngestionAgent()
             await agent.process_inbox()
             
             mock_gmail.extract_attachments.assert_called_with('msg_2')
             # Should NOT mark as read if logic assumes only processing entails reading? 
             # Actually code marks read even if no attachments for now to avoid loops, 
             # but let's check what I implemented. 
             # Ah, I implemented: if not attachments: continue. So it WON'T mark as read.
             mock_gmail.mark_as_read.assert_not_called()
             mock_db.invoices.create.assert_not_called()
