import sys
import os
sys.path.append(os.getcwd())
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.memory.semantic_memory import SemanticMemory
from app.models.memory import Memory, MemoryType

@pytest.mark.asyncio
async def test_store_learning_generates_embedding():
    memory = Memory(
        type=MemoryType.REFLECTION,
        observation="Invoice from Apple had mixed VAT",
        learning="Apple always uses 20% for hardware and 0% for books",
        vendor_name="Apple Ltd",
        confidence=0.9
    )
    
    # Mock sentence_transformers in sys.modules to prevent DLL loading
    mock_st = MagicMock()
    with patch.dict("sys.modules", {"sentence_transformers": mock_st}), \
         patch("app.memory.semantic_memory.db") as mock_db:
        
        # Setup mock model
        mock_model = MagicMock()
        mock_st.SentenceTransformer.return_value = mock_model
        
        # mock encode to return something with tolist()
        mock_embedding = MagicMock()
        mock_embedding.tolist.return_value = [0.1] * 384
        mock_model.encode.return_value = mock_embedding
        
        # Mock DB
        mock_raw_db = MagicMock()
        mock_db.db = mock_raw_db
        mock_raw_db.__getitem__.return_value.insert_one = AsyncMock()
        
        sm = SemanticMemory()
        await sm.store_learning(memory)
        
        # Verify embedding was generated and stored
        assert memory.embedding == [0.1] * 384
        mock_raw_db.__getitem__.assert_called_with("memories")

@pytest.mark.asyncio
async def test_retrieve_similar_cases_pipeline():
    mock_st = MagicMock()
    with patch.dict("sys.modules", {"sentence_transformers": mock_st}), \
         patch("app.memory.semantic_memory.db") as mock_db:
        
        # Setup mock model
        mock_model = MagicMock()
        mock_st.SentenceTransformer.return_value = mock_model
        
        mock_embedding = MagicMock()
        mock_embedding.tolist.return_value = [0.1] * 384
        mock_model.encode.return_value = mock_embedding
        
        # Mock DB Aggregation
        mock_raw_db = MagicMock()
        mock_db.db = mock_raw_db
        mock_cursor = MagicMock()
        mock_cursor.to_list = AsyncMock(return_value=[{"observation": "Match!", "similarity_score": 0.9}])
        mock_raw_db.__getitem__.return_value.aggregate.return_value = mock_cursor
        
        sm = SemanticMemory()
        results = await sm.retrieve_similar_cases("How does Apple handle VAT?", min_similarity=0.8)
        
        assert len(results) == 1
        assert results[0]["similarity_score"] == 0.9
        
        # Verify the pipeline contains $vectorSearch
        pipeline = mock_raw_db.__getitem__.return_value.aggregate.call_args[0][0]
        assert "$vectorSearch" in pipeline[0]
        assert pipeline[0]["$vectorSearch"]["queryVector"] == [0.1] * 384

@pytest.mark.asyncio
async def test_prune_memories():
    with patch("app.memory.semantic_memory.db") as mock_db:
        mock_raw_db = MagicMock()
        mock_db.db = mock_raw_db
        mock_raw_db.__getitem__.return_value.delete_many = AsyncMock(return_value=MagicMock(deleted_count=5))
        
        sm = SemanticMemory()
        await sm.prune_memories(min_confidence=0.4)
        
        mock_raw_db.__getitem__.return_value.delete_many.assert_called_with({"confidence": {"$lt": 0.4}})
