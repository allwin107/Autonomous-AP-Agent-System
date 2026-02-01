from typing import Annotated, Any, Dict, Type, TypeVar
from pydantic import BaseModel, BeforeValidator, Field, ConfigDict
from bson import ObjectId

# Helper to handle ObjectId as string
PyObjectId = Annotated[str, BeforeValidator(str)]

T = TypeVar("T", bound="MongoModel")

class MongoModel(BaseModel):
    """
    Base model for MongoDB documents with _id handling and serialization helpers.
    """
    id: PyObjectId | None = Field(default=None, alias="_id")
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={
            ObjectId: str
        }
    )

    @classmethod
    def from_mongo(cls: Type[T], data: Dict[str, Any]) -> T:
        """Convert MongoDB document to Pydantic model."""
        if not data:
            return None
        id = data.pop("_id", None)
        return cls(id=id, **data)

    def to_mongo(self, exclude_none: bool = False) -> Dict[str, Any]:
        """Convert Pydantic model to MongoDB document."""
        data = self.model_dump(by_alias=True, exclude_none=exclude_none)
        if data.get("_id") is None:
            data.pop("_id", None)
        return data
