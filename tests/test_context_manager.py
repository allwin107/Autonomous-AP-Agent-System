import sys
import os
sys.path.append(os.getcwd())
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from app.memory.context_manager import ContextManager

@pytest.fixture
def manager():
    # Pass a valid tiktoken model name or it will fallback to base
    return ContextManager(model_name="gpt-4")

@pytest.mark.asyncio
async def test_estimate_tokens(manager):
    text = "Hello world"
    tokens = manager.estimate_tokens(text)
    assert tokens > 0
    
    data = {"key": "value"}
    tokens_json = manager.estimate_tokens(data)
    assert tokens_json > tokens

@pytest.mark.asyncio
async def test_prepare_context_prioritization(manager):
    state = {
        "invoice_id": "INV-123",
        "current_state": "VALIDATION",
        "extracted_data": {"total": 100.0},
        "raw_text": "A very long invoice text..." * 10
    }
    
    # Mock sentence_transformers in sys.modules to prevent DLL loading
    mock_st = MagicMock()
    with patch.dict("sys.modules", {"sentence_transformers": mock_st}), \
         patch("app.memory.context_manager.semantic_memory") as mock_sm:
        mock_sm.retrieve_similar_cases = AsyncMock(return_value=[])
        
        context = await manager.prepare_context_for_llm(state, "VALIDATION: Test task")
        
        assert "# ESSENTIAL CONTEXT" in context
        assert "INV-123" in context
        assert "VALIDATION" in context

@pytest.mark.asyncio
async def test_context_truncation_trigger(manager):
    # Create an artificially small limit for testing summarization
    manager.max_context_tokens = 50 
    
    state = {
        "invoice_id": "MOD-888",
        "raw_text": "This is a very long text that will definitely exceed the fifty token limit we set for this specific test case."
    }
    
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="Summary: Over limit"))]
    
    mock_st = MagicMock()
    with patch.dict("sys.modules", {"sentence_transformers": mock_st}), \
         patch("app.memory.context_manager.groq_tool") as mock_groq:
        mock_groq.client.chat.completions.create.return_value = mock_response
        
        context = await manager.prepare_context_for_llm(state, "TEST: Truncation")
        
        assert "Summary: Over limit" in context
        mock_groq.client.chat.completions.create.assert_called()

@pytest.mark.asyncio
async def test_task_specific_policies(manager):
    mock_st = MagicMock()
    with patch.dict("sys.modules", {"sentence_transformers": mock_st}), \
         patch("app.memory.context_manager.semantic_memory") as mock_sm:
        mock_sm.retrieve_similar_cases = AsyncMock(return_value=[])
        
        context = await manager.prepare_context_for_llm({"invoice_id": "POL-1"}, "VALIDATION")
        assert "# TASK-SPECIFIC DATA" in context
        assert "Standard UK VAT rate" in context

