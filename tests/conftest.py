import sys
from unittest.mock import MagicMock

print("DEBUG: Loading conftest.py and mocking heavy modules...")
# Global mock for components that cause DLL initialization issues
mock_st = MagicMock()
mock_torch = MagicMock()

# Smarter tiktoken mock to allow token counting logic to pass
mock_encoding = MagicMock()
def mock_encode(text):
    if isinstance(text, dict):
        text = str(text)
    return list(range(len(text) // 4 + 1)) # Rough estimate: 1 token per 4 chars

mock_encoding.encode.side_effect = mock_encode
mock_tiktoken = MagicMock()
mock_tiktoken.encoding_for_model.return_value = mock_encoding
mock_tiktoken.get_encoding.return_value = mock_encoding


sys.modules["sentence_transformers"] = mock_st
sys.modules["torch"] = mock_torch
sys.modules["tiktoken"] = mock_tiktoken
print("DEBUG: Mocks established.")





import pytest
from unittest.mock import AsyncMock, patch

from datetime import datetime
from app.models.invoice import Invoice, InvoiceData, LineItem, InvoiceStatus

@pytest.fixture
def mock_db():
    with patch("app.database.db") as mock:
        # Mock collections
        mock.invoices = AsyncMock()
        mock.vendors = AsyncMock()
        mock.audit = AsyncMock()
        mock.config = AsyncMock()
        mock.fs = MagicMock() # GridFS mock
        mock._db = MagicMock() # The raw motor database object
        yield mock


@pytest.fixture
def mock_llm():
    with patch("app.tools.groq_llm.groq_tool") as mock:
        mock.generate_structured = MagicMock()
        yield mock

@pytest.fixture
def sample_invoice_data():
    return InvoiceData(
        vendor_name="Test Vendor Ltd",
        vendor_id="V-999",
        invoice_number="INV-2024-001",
        invoice_date=datetime(2024, 1, 1),
        line_items=[
            LineItem(item_id=1, description="Office Supplies", quantity=10, unit_price=5.0, line_total=50.0)
        ],
        subtotal=50.0,
        vat_rate=0.2,
        vat_amount=10.0,
        total=60.0,
        currency="GBP"
    )

@pytest.fixture
def sample_invoice(sample_invoice_data):
    return Invoice(
        invoice_id="INV-001",
        company_id="COMP-A",
        status=InvoiceStatus.INGESTION,
        data=sample_invoice_data
    )

@pytest.fixture
def mock_semantic_memory():
    with patch("app.memory.semantic_memory.semantic_memory") as mock:
        mock.store_learning = AsyncMock()
        mock.retrieve_similar_cases = AsyncMock(return_value=[])
        yield mock
