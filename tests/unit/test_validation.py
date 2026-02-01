import sys
import os
sys.path.append(os.getcwd())
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from app.agents.validation import ValidationAgent
from app.models.invoice import InvoiceStatus
from app.models.vendor import Vendor, VerificationStatus

@pytest.mark.asyncio
async def test_validation_node_success(mock_db, sample_invoice):
    # Setup Mock Invoice
    sample_invoice.invoice_id = "inv_valid"
    sample_invoice.status = InvoiceStatus.EXTRACTION
    mock_db.invoices.get_by_field.return_value = sample_invoice
    
    # Mock Vendor (Verified)
    mock_vendor = MagicMock(spec=Vendor)
    mock_vendor.vendor_id = "ven_1"
    mock_vendor.approval_status = "APPROVED" # Fixed field name
    mock_db.vendors.get_by_field.return_value = mock_vendor
    
    # Mock Tools
    with patch("app.agents.validation.duplicate_detector") as mock_dup, \
         patch("app.agents.validation.vat_validator") as mock_vat, \
         patch("app.agents.validation.fraud_detector") as mock_fraud, \
         patch("app.agents.validation.db") as mock_db_local, \
         patch("app.agents.validation.verification_tool") as mock_ver, \
         patch("app.agents.validation.semantic_memory") as mock_sm, \
         patch("app.agents.validation.context_manager") as mock_cm:
        
        mock_db_local.invoices = mock_db.invoices
        mock_db_local.vendors = mock_db.vendors
        
        # Async calls
        mock_dup.check_duplicates = AsyncMock(return_value={"is_duplicate": False})
        mock_fraud.check_bank_details_change = AsyncMock(return_value=False)
        mock_ver.initiate_verification = AsyncMock()
        mock_cm.prepare_context_for_llm = AsyncMock(return_value="mock context")
        mock_sm.retrieve_similar_cases = AsyncMock(return_value=[])
        
        # Sync calls
        mock_vat.validate_vat = MagicMock(return_value={"valid": True, "details": "OK"})
        mock_fraud.analyze_fraud_risk = MagicMock(return_value={"fraud_score": 0.0, "flags": []})
        
        agent = ValidationAgent()
        state = {
            "invoice_id": "inv_valid",
            "company_id": "acme",
            "current_state": "VALIDATION",
            "invoice_data": sample_invoice.data.model_dump(),
            "validation_results": None,
            "matching_results": None,
            "risk_score": 0.0,
            "human_approval_required": False,
            "errors": []
        }
        result = await agent.validation_node(state)
        
        assert result["current_state"] == InvoiceStatus.MATCHING
        assert result["validation_results"]["vat_valid"] is True

@pytest.mark.asyncio
async def test_validation_node_vat_failure(mock_db, sample_invoice):
    agent = ValidationAgent()
    sample_invoice.status = InvoiceStatus.EXTRACTION
    mock_db.invoices.get_by_field.return_value = sample_invoice
    
    with patch("app.agents.validation.duplicate_detector") as mock_dup, \
         patch("app.agents.validation.vat_validator") as mock_vat, \
         patch("app.agents.validation.fraud_detector") as mock_fraud, \
         patch("app.agents.validation.vat_corrector") as mock_corr, \
         patch("app.agents.validation.db") as mock_db_local, \
         patch("app.agents.validation.semantic_memory") as mock_sm, \
         patch("app.agents.validation.context_manager") as mock_cm:
        
        mock_db_local.invoices = mock_db.invoices
        mock_db_local.vendors = mock_db.vendors
        
        mock_dup.check_duplicates = AsyncMock(return_value={"is_duplicate": False})
        mock_fraud.check_bank_details_change = AsyncMock(return_value=False)
        mock_vat.validate_vat = MagicMock(return_value={"valid": False, "details": "Wrong VAT"})
        mock_fraud.analyze_fraud_risk = MagicMock(return_value={"fraud_score": 0.1, "flags": []})
        mock_corr.generate_correction_request = AsyncMock()
        mock_cm.prepare_context_for_llm = AsyncMock(return_value="mock context")
        mock_sm.retrieve_similar_cases = AsyncMock(return_value=[])
        
        state = {
            "invoice_id": "inv_vat_fail",
            "company_id": "acme",
            "current_state": "VALIDATION",
            "invoice_data": sample_invoice.data.model_dump(),
            "validation_results": None,
            "matching_results": None,
            "risk_score": 0.0,
            "human_approval_required": False,
            "errors": []
        }
        result = await agent.validation_node(state)
        
        assert result["current_state"] == InvoiceStatus.AWAITING_CORRECTION
        mock_corr.generate_correction_request.assert_called()

@pytest.mark.asyncio
async def test_validation_node_duplicate(mock_db, sample_invoice):
    sample_invoice.invoice_id = "inv_dup"
    mock_db.invoices.get_by_field.return_value = sample_invoice
    
    with patch("app.agents.validation.duplicate_detector") as mock_dup, \
         patch("app.agents.validation.vat_validator") as mock_vat, \
         patch("app.agents.validation.fraud_detector") as mock_fraud, \
         patch("app.agents.validation.db") as mock_db_local:
        
        mock_db_local.invoices = mock_db.invoices
        mock_db_local.vendors = mock_db.vendors
        
        mock_dup.check_duplicates = AsyncMock(return_value={"is_duplicate": True, "match_type": "EXACT", "conflicting_invoice_id": "OLD-123"})
        mock_fraud.check_bank_details_change = AsyncMock(return_value=False)
        mock_vat.validate_vat = MagicMock(return_value={"valid": True})
        mock_fraud.analyze_fraud_risk = MagicMock(return_value={"fraud_score": 0.0, "flags": []})
        
        agent = ValidationAgent()
        state = {
            "invoice_id": "inv_dup",
            "company_id": "acme",
            "current_state": "VALIDATION",
            "invoice_data": sample_invoice.data.model_dump(),
            "validation_results": None,
            "matching_results": None,
            "risk_score": 0.0,
            "human_approval_required": False,
            "errors": []
        }
        result = await agent.validation_node(state)
        
        assert result["current_state"] == InvoiceStatus.EXCEPTION
        assert result["validation_results"]["is_duplicate"] is True
