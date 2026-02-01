from typing import Annotated, Any
from pydantic import BaseModel, BeforeValidator, Field, ConfigDict

# Helper to handle ObjectId as string
PyObjectId = Annotated[str, BeforeValidator(str)]

class MongoModel(BaseModel):
    """Base model for MongoDB documents with _id handling"""
    id: PyObjectId | None = Field(default=None, alias="_id")
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={
            # Add any custom encoders here if needed
        }
    )
