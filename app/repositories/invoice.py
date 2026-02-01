from typing import List, Optional
from motor.motor_asyncio import AsyncIOMotorClientSession
from app.repositories.base import BaseRepository
from app.models.invoice import Invoice

class InvoiceRepository(BaseRepository[Invoice]):
    
    async def get_by_invoice_number(self, invoice_number: str, company_id: str) -> Optional[Invoice]:
        return await self.get_by_field("invoice_number", invoice_number) # Should also filter by company_id ideally in finding

    async def get_duplicate_candidates(self, vendor_name: str, total_amount: float, date_range_start, date_range_end) -> List[Invoice]:
        """Find invoices that might be duplicates based on vendor, amount, and date window."""
        filter = {
            "data.vendor_name": vendor_name,
            "data.total": total_amount,
            "data.invoice_date": {"$gte": date_range_start, "$lte": date_range_end},
            "status": {"$ne": "REJECTED"}
        }
        return await self.list(filter, limit=10)

    async def update_status(self, invoice_id: str, status: str, session: AsyncIOMotorClientSession = None) -> bool:
        """Update invoice status transactionally."""
        result = await self.collection.update_one(
            {"invoice_id": invoice_id},
            {"$set": {"status": status}},
            session=session
        )
        return result.modified_count > 0
