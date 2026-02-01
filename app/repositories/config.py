from typing import Optional
from app.repositories.base import BaseRepository
from app.models.config import CompanyConfig

class ConfigRepository(BaseRepository[CompanyConfig]):
    async def get_by_company_id(self, company_id: str) -> Optional[CompanyConfig]:
        doc = await self.collection.find_one({"company_id": company_id})
        return self.model_cls.from_mongo(doc) if doc else None
