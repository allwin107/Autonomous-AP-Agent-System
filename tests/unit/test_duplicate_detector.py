import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.tools.duplicate_detector import DuplicateDetector
from datetime import datetime

@pytest.mark.asyncio
async def test_check_duplicates_none_found(mock_db):
    with patch("app.tools.duplicate_detector.db") as mock_db_local:
        mock_db_local.invoices = mock_db.invoices
        detector = DuplicateDetector()
        mock_db_local.invoices.list = AsyncMock(return_value=[])
        
        result = await detector.check_duplicates(
            "INV-001", "Vendor A", "NUM-123", 100.0, datetime.now(), []
        )
        
        assert result["is_duplicate"] is False

@pytest.mark.asyncio
async def test_check_duplicates_exact_match(mock_db):
    with patch("app.tools.duplicate_detector.db") as mock_db_local:
        mock_db_local.invoices = mock_db.invoices
        detector = DuplicateDetector()
        # Mock finding an invoice with same number and vendor
        mock_db_local.invoices.list = AsyncMock(return_value=[
            MagicMock(invoice_id="INV-OLD", status="INGESTION", data=MagicMock(invoice_number="NUM-123", vendor_name="Vendor A"))
        ])
        
        result = await detector.check_duplicates(
            "INV-NEW", "Vendor A", "NUM-123", 100.0, datetime.now(), []
        )
        
        assert result["is_duplicate"] is True
        assert result["match_type"] == "EXACT_NUMBER"
        assert result["conflicting_invoice_id"] == "INV-OLD"


