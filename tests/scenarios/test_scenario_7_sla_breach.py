import sys
import os
sys.path.append(os.getcwd())
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from datetime import datetime, timedelta
from app.agents.sla_monitor import sla_monitor
from app.models.invoice import Invoice, InvoiceStatus, InvoiceData

@pytest.mark.asyncio
async def test_check_payment_deadlines_critical():
    # Setup: Invoice due in 12 hours
    due_date = datetime.utcnow() + timedelta(hours=12)
    data = InvoiceData(
        vendor_name="V", invoice_number="N", 
        invoice_date=datetime.utcnow(), subtotal=100.0, total=100.0,
        due_date=due_date
    )
    invoice = Invoice(
        invoice_id="inv_critical", company_id="c1", status=InvoiceStatus.AWAITING_APPROVAL,
        data=data, urgency="NORMAL"
    )
    
    # Mock DB
    with patch("app.agents.sla_monitor.db") as mock_db_instance, \
         patch("app.tools.notification_tool.notification_tool.send_notification") as mock_notif:
         
        # mock_db_instance is the DATABASE instance from app.database
        mock_raw_db = MagicMock()
        type(mock_db_instance).db = PropertyMock(return_value=mock_raw_db)
        
        # Mock find result (as async iterable/cursor)
        mock_cursor = MagicMock()
        mock_cursor.to_list = AsyncMock(return_value=[invoice.model_dump(by_alias=True)])
        mock_raw_db.__getitem__.return_value.find.return_value = mock_cursor
        mock_raw_db.__getitem__.return_value.update_one = AsyncMock()
        
        await sla_monitor.check_payment_deadlines()
        
        # Verify escalation to CRITICAL
        mock_raw_db.__getitem__.return_value.update_one.assert_called()
        args, kwargs = mock_raw_db.__getitem__.return_value.update_one.call_args
        assert args[1]["$set"]["urgency"] == "CRITICAL"
        
        # Verify notification sent to CFO
        mock_notif.assert_called()
        notif_args = mock_notif.call_args
        assert "cfo@company.com" in notif_args.kwargs["users"]

@pytest.mark.asyncio
async def test_check_approval_sla_breach():
    # Setup: Invoice pending approval for 50 hours (SLA is 48)
    updated_at = datetime.utcnow() - timedelta(hours=50)
    invoice = Invoice(
        invoice_id="inv_breached", company_id="c1", 
        status=InvoiceStatus.AWAITING_APPROVAL,
        updated_at=updated_at, sla_status="COMPLIANT"
    )
    
    with patch("app.agents.sla_monitor.db") as mock_db_instance, \
         patch("app.tools.notification_tool.notification_tool.send_notification") as mock_notif:
         
        mock_raw_db = MagicMock()
        type(mock_db_instance).db = PropertyMock(return_value=mock_raw_db)
        
        mock_cursor = MagicMock()
        mock_cursor.to_list = AsyncMock(return_value=[invoice.model_dump(by_alias=True)])
        mock_raw_db.__getitem__.return_value.find.return_value = mock_cursor
        mock_raw_db.__getitem__.return_value.update_one = AsyncMock()
        
        # Mock repository
        mock_db_instance.invoices = MagicMock()
        mock_db_instance.invoices.update = AsyncMock()
        
        await sla_monitor.check_approval_slas(sla_hours=48)
        
        # Verify sla_status updated to BREACHED via repository
        mock_db_instance.invoices.update.assert_called_with("inv_breached", {"sla_status": "BREACHED"})
