from typing import Generic, TypeVar, Any, Dict, List, Optional
from motor.motor_asyncio import AsyncIOMotorCollection
from bson import ObjectId
from app.models.base import MongoModel

T = TypeVar("T", bound=MongoModel)

class BaseRepository(Generic[T]):
    def __init__(self, collection: AsyncIOMotorCollection, model_cls: type[T]):
        self.collection = collection
        self.model_cls = model_cls

    async def get(self, id: str) -> Optional[T]:
        """Get a document by ID."""
        doc = await self.collection.find_one({"_id": ObjectId(id)})
        return self.model_cls.from_mongo(doc) if doc else None
    
    async def get_by_field(self, field: str, value: Any) -> Optional[T]:
        """Get a document by a specific field."""
        doc = await self.collection.find_one({field: value})
        return self.model_cls.from_mongo(doc) if doc else None

    async def list(self, filter: Dict[str, Any] = {}, skip: int = 0, limit: int = 100) -> List[T]:
        """List documents with optional filter and pagination."""
        cursor = self.collection.find(filter).skip(skip).limit(limit)
        docs = await cursor.to_list(length=limit)
        return [self.model_cls.from_mongo(doc) for doc in docs]

    async def create(self, model: T) -> T:
        """Create a new document."""
        data = model.to_mongo()
        result = await self.collection.insert_one(data)
        model.id = str(result.inserted_id)
        return model

    async def update(self, id: str, update_data: Dict[str, Any]) -> Optional[T]:
        """Update a document by ID."""
        # Using $set for partial updates
        result = await self.collection.update_one(
            {"_id": ObjectId(id)},
            {"$set": update_data}
        )
        if result.modified_count == 0:
            # Check if it existed but nothing changed OR it didn't exist
            # For this simple base, we'll just try to fetch it.
            pass
        
        return await self.get(id)

    async def delete(self, id: str) -> bool:
        """Delete a document by ID."""
        result = await self.collection.delete_one({"_id": ObjectId(id)})
        return result.deleted_count > 0

    async def count(self, filter: Dict[str, Any] = {}) -> int:
        """Count documents matching a filter."""
        return await self.collection.count_documents(filter)
