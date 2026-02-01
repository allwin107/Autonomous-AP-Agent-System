import sys
import os
sys.path.append(os.getcwd())
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.agents.reflection import ReflectionAgent
from app.models.invoice import Invoice, InvoiceData, InvoiceStatus
from app.models.memory import Memory, MemoryType

@pytest.mark.asyncio
async def test_reflect_on_failure_stores_memory():
    mock_invoice = MagicMock(spec=Invoice)
    mock_invoice.invoice_id = "INV-001"
    mock_invoice.data = MagicMock(vendor_name="Acme Corp", vendor_id="V-001", total=100.0)
    mock_invoice.status = InvoiceStatus.EXCEPTION
    
    # Mock LLM and Semantic Memory
    mock_llm = MagicMock()
    mock_llm.generate_structured.return_value = {
        "pattern_identified": "Repeated OCR failure for Acme",
        "is_vendor_specific": True,
        "recommended_action": "Use manual verification for Acme",
        "confidence": 0.9
    }
    
    mock_sm = AsyncMock()
    
    # Mock DB
    mock_db = MagicMock()
    mock_db.invoices.get_by_field = AsyncMock(return_value=mock_invoice)
    mock_db.audit.get_for_invoice = AsyncMock(return_value=[])
    
    agent = ReflectionAgent()
    
    with patch("app.agents.reflection.groq_tool", mock_llm), \
         patch("app.agents.reflection.semantic_memory", mock_sm), \
         patch("app.agents.reflection.db", mock_db):
        
        await agent.reflect_on_failure("INV-001", "EXTRACTION_FAILURE")
        
        # Verify LLM was called
        mock_llm.generate_structured.assert_called()
        # Verify memory was stored
        mock_sm.store_learning.assert_called()
        memory_stored = mock_sm.store_learning.call_args[0][0]
        assert memory_stored.pattern == "Repeated OCR failure for Acme"
        assert memory_stored.confidence == 0.9

@pytest.mark.asyncio
async def test_apply_learnings_retrieves_hints():
    mock_invoice = MagicMock(spec=Invoice)
    mock_invoice.data = MagicMock(vendor_name="Acme Corp")
    
    # Mock Semantic Memory to return a match
    mock_sm = MagicMock()
    mock_sm.retrieve_similar_cases = AsyncMock(return_value=[
        {"learning": "Acme needs manual review", "confidence": 0.9}
    ])
    
    agent = ReflectionAgent()
    with patch("app.agents.reflection.semantic_memory", mock_sm):
        hints = await agent.apply_learnings(mock_invoice)
        
        assert len(hints) == 1
        assert "Acme needs manual review" in hints[0]
