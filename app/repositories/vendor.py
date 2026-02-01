from typing import Optional
from app.repositories.base import BaseRepository
from app.models.vendor import Vendor

class VendorRepository(BaseRepository[Vendor]):
    async def get_by_name(self, name: str, company_id: str) -> Optional[Vendor]:
        doc = await self.collection.find_one({"name": name, "company_id": company_id})
        return self.model_cls.from_mongo(doc) if doc else None
