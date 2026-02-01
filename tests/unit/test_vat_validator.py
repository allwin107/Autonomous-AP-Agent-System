import pytest
from app.tools.vat_validator import vat_validator
from app.models.invoice import InvoiceData, LineItem
from datetime import datetime

def test_validate_vat_correct():
    data = InvoiceData(
        subtotal=100.0,
        vat_amount=20.0,
        vat_rate=0.2,
        total=120.0,
        vendor_name="Acme",
        invoice_number="INV-001",
        invoice_date=datetime.now(),
        line_items=[]
    )
    result = vat_validator.validate_vat(data)
    assert result["valid"] is True

def test_validate_vat_incorrect():
    data = InvoiceData(
        subtotal=100.0,
        vat_amount=15.0, # Incorrect for 20%
        vat_rate=0.2,
        total=115.0,
        vendor_name="Acme",
        invoice_number="INV-002",
        invoice_date=datetime.now(),
        line_items=[]
    )
    result = vat_validator.validate_vat(data)
    assert result["valid"] is False
    assert "does not match" in result["details"]

def test_validate_vat_zero_vat():
    data = InvoiceData(
        subtotal=100.0,
        vat_amount=0.0,
        vat_rate=0.0,
        total=100.0,
        vendor_name="Acme",
        invoice_number="INV-003",
        invoice_date=datetime.now(),
        line_items=[]
    )
    result = vat_validator.validate_vat(data)
    assert result["valid"] is True
