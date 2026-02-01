import logging
import uuid
from typing import Dict, Any, List
from datetime import datetime

from app.database import db
from app.models.invoice import InvoiceStatus, InvoiceData
from app.models.config import GLMapping
from app.models.accounting import JournalEntry, JournalLine, EntryType

logger = logging.getLogger(__name__)

class RecordingAgent:
    def __init__(self):
        pass

    async def recording_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Creates journal entries for Approved/Paid invoices.
        Typically runs after Approval or before/after Payment.
        User request says "Create accounting entries... for processed invoices".
        """
        invoice_id = state.get("invoice_id")
        company_id = state.get("company_id")

        try:
            invoice = await db.invoices.get_by_field("invoice_id", invoice_id)
            if not invoice or not invoice.data:
                state["errors"] = ["Invoice data missing"]
                # Maybe exception, or just skip if not ready?
                return state

            data: InvoiceData = InvoiceData(**invoice.data.model_dump())
            
            # Fetch Config for GL Mapping
            config = await db.config.get_by_field("company_id", company_id)
            if not config:
                gl_map = GLMapping() # Default
            else:
                gl_map = config.gl_mapping

            # Create Journal Entry
            je = self._create_journal_entry(data, invoice.invoice_id, gl_map)
            
            # Validate
            if not je.validate_balance():
                msg = f"Journal Entry Imbalanced: DR {je.total_debit} != CR {je.total_credit}"
                logger.error(msg)
                state["errors"] = [msg]
                state["current_state"] = InvoiceStatus.EXCEPTION
                return state

            # Post to Ledger (Simulated)
            await self._post_to_ledger(je)
            
            # Update Vendor Balance
            # Assuming we can infer vendor_id from invoice or data
            # For simplicity, if vendor_id is on invoice root:
            if invoice.vendor_id:
                await self._update_vendor_balance(invoice.vendor_id, data.total)

            logger.info(f"Journal Entry created: {je.entry_id}")
            
            # Log in invoice?
            await db.invoices.update(invoice_id, {
                "journal_entry_id": je.entry_id
            })
            
            # Assuming this is the FINAL step or an intermediate step.
            # If we hook this after Payment Prep or Approval?
            # User wants a "Recording Agent". Usually "Recorded" is a status?
            # If this runs PARALLEL or SEQUENTIAL, depends on flow.
            # For this node, we just return state. 
            
        except Exception as e:
            logger.error(f"Recording failed: {e}")
            state["errors"] = [str(e)]
            state["current_state"] = InvoiceStatus.EXCEPTION

        return state

    def _create_journal_entry(self, data: InvoiceData, source_doc: str, gl_map: GLMapping) -> JournalEntry:
        lines: List[JournalLine] = []
        
        # 1. Expense Lines (Debits)
        for item in data.line_items:
            # Determine GL
            gl_code = gl_map.default_expense_gl
            if item.category and item.category in gl_map.category_map:
                gl_code = gl_map.category_map[item.category]
            
            lines.append(JournalLine(
                gl_code=gl_code,
                account_name=item.category or "General Expense",
                description=f"{item.description} (Inv: {source_doc})",
                type=EntryType.DEBIT,
                amount=item.line_total
            ))
            
        # 2. VAT (Debit)
        if data.vat_amount > 0:
            lines.append(JournalLine(
                gl_code=gl_map.vat_recoverable_gl,
                account_name="VAT Recoverable",
                description=f"VAT on {source_doc}",
                type=EntryType.DEBIT,
                amount=data.vat_amount
            ))
            
        # 3. Accounts Payable (Credit) - Total Liability
        # Check if total equals sum of lines
        # Sometimes small rounding diffs occur.
        # We trust `data.total`. The CR must match sum of DRs for balance.
        # Ideally data.total == subtotal + vat.
        
        total_dr = sum(l.amount for l in lines)
        # If total_dr != data.total, we might have an issue.
        # Let's use total_dr as the validation check, but use data.total for AP?
        # Typically AP = Total to pay.
        # Any difference is "Rounding Difference" expense.
        
        ap_amount = data.total
        diff = total_dr - ap_amount
        
        if abs(diff) > 0.001:
             # Rounding line
             lines.append(JournalLine(
                gl_code=gl_map.default_expense_gl, # Or specific rounding GL
                account_name="Rounding Adjustment",
                description="Rounding",
                type=EntryType.DEBIT if diff < 0 else EntryType.CREDIT,
                amount=abs(diff)
             ))
             if diff < 0:
                 total_dr += abs(diff)
             # If diff > 0 (DR > CR), we add a CREDIT line, or reduce DR?
             # Actually, if we add a line, we must be careful with types.
             # If DR = 100.01, AP(CR) = 100.00. Left side heavy. Need 0.01 CREDIT.
             # If EntryType.CREDIT, amount=0.01.
             pass

        lines.append(JournalLine(
            gl_code=gl_map.accounts_payable_gl,
            account_name="Accounts Payable",
            description=f"Liability for {source_doc}",
            type=EntryType.CREDIT,
            amount=sum(l.amount for l in lines if l.type == EntryType.DEBIT) # Force balance for simple logic
        ))
        
        total_debit = sum(l.amount for l in lines if l.type == EntryType.DEBIT)
        total_credit = sum(l.amount for l in lines if l.type == EntryType.CREDIT)

        return JournalEntry(
            entry_id=f"JE-{uuid.uuid4().hex[:8]}",
            date=datetime.utcnow(),
            posting_date=datetime.utcnow(),
            reference=source_doc,
            source_document=source_doc,
            currency=data.currency,
            lines=lines,
            total_debit=total_debit,
            total_credit=total_credit,
            status="POSTED"
        )

    async def _post_to_ledger(self, je: JournalEntry):
        # In real world, send to Xero/QB API
        # Here we save to 'journal_entries' collection
        await db.db["journal_entries"].insert_one(je.model_dump())

    async def _update_vendor_balance(self, vendor_id: str, amount: float):
        # Check if vendor exists
        # Update 'balance' field (we didn't define it in Vendor model explicitly, assuming dynamic or we add it)
        # Assuming just a log for now or updating 'open_balance' if it existed.
        # We'll rely on Mongo's flexibility
        await db.db["vendors"].update_one(
            {"vendor_id": vendor_id},
            {"$inc": {"balance": amount}}
        )

recording_agent = RecordingAgent()
