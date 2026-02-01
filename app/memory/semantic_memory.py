import logging
import asyncio
from typing import List, Dict, Any, Optional
from app.models.memory import Memory, MemoryType
from app.database import db

logger = logging.getLogger(__name__)

class SemanticMemory:
    """
    Handles storage and retrieval of AP learnings using vector embeddings.
    """
    def __init__(self, embedding_model: str = "all-MiniLM-L6-v2"):
        self.model_name = embedding_model
        self._model = None # Lazy load to save memory if not used
        self.index_name = "vector_index"
        self.collection_name = "memories"

    @property
    def model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading embedding model: {self.model_name}")
            # Ensure this runs in a thread if it's slow, but for init it's fine
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def generate_embedding(self, text: str) -> List[float]:
        """Generates a 384-dimensional embedding vector."""
        # SentenceTransformer.encode returns a numpy array
        embedding = self.model.encode(text)
        return embedding.tolist()

    async def store_learning(self, memory: Memory):
        """
        Generates embedding and stores the memory in MongoDB.
        """
        # Embed the combination of observation and learning
        combined_text = f"Scenario: {memory.observation} | Learning: {memory.learning}"
        memory.embedding = self.generate_embedding(combined_text)
        
        # Insert into memories collection
        doc = memory.model_dump(by_alias=True)
        await db.db[self.collection_name].insert_one(doc)
        logger.info(f"Stored {memory.type} memory for vendor {memory.vendor_name}")

    async def retrieve_similar_cases(self, query: str, limit: int = 5, min_similarity: float = 0.7) -> List[Dict[str, Any]]:
        """
        Uses Atlas Vector Search to find similar past experiences.
        """
        query_vector = self.generate_embedding(query)
        
        # aggregation pipeline for Atlas Vector Search
        pipeline = [
            {
                "$vectorSearch": {
                    "index": self.index_name,
                    "path": "embedding",
                    "queryVector": query_vector,
                    "numCandidates": limit * 10,
                    "limit": limit
                }
            },
            {
                "$addFields": {
                    "similarity_score": {"$meta": "vectorSearchScore"}
                }
            },
            {
                "$match": {
                    "similarity_score": {"$gte": min_similarity}
                }
            },
            {
                "$project": {"embedding": 0} # Don't return the raw vector
            }
        ]
        
        try:
            cursor = db.db[self.collection_name].aggregate(pipeline)
            results = await cursor.to_list(length=limit)
            return results
        except Exception as e:
            logger.error(f"Vector search failed (check if index {self.index_name} exists): {e}")
            return []

    async def get_vendor_patterns(self, vendor_name: str) -> List[Memory]:
        """
        Retrieves established patterns for a specific vendor.
        """
        cursor = db.db[self.collection_name].find({
            "vendor_name": vendor_name,
            "type": MemoryType.PATTERN
        })
        docs = await cursor.to_list(length=20)
        return [Memory(**doc) for doc in docs]

    async def prune_memories(self, min_confidence: float = 0.3):
        """
        Removes outdated or low-relevance memories to keep the index clean.
        """
        result = await db.db[self.collection_name].delete_many({
            "confidence": {"$lt": min_confidence}
        })
        logger.info(f"Pruned {result.deleted_count} low-confidence memories.")

# Singleton instance
semantic_memory = SemanticMemory()
