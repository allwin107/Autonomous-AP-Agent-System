import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from app.database import db
from app.models.invoice import InvoiceStatus, InvoiceData, MatchingResults, LineItem
from app.models.purchase_order import PurchaseOrder
from app.models.grn import GoodsReceiptNote

logger = logging.getLogger(__name__)

class MatchingAgent:
    def __init__(self):
        pass

    async def matching_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes 3-way matching logic.
        """
        invoice_id = state.get("invoice_id")
        company_id = state.get("company_id")
        
        if not invoice_id:
            logger.error("No invoice id in matching node")
            state["errors"] = ["Missing invoice_id"]
            return state

        try:
            # 1. Fetch Invoice
            invoice = await db.invoices.get_by_field("invoice_id", invoice_id)
            if not invoice or not invoice.data:
                state["errors"] = ["Invoice data missing"]
                return state

            data: InvoiceData = InvoiceData(**invoice.data.model_dump())
            
            # 2. Identify PO
            po_number = data.po_reference
            
            # If no PO reference, determining logic:
            # - Is PO required? (Company config)
            # - If small amount, maybe NO_PO match is allowed?
            # For now, if no PO -> AWAITING_APPROVAL (Manager review)
            if not po_number:
                logger.info(f"No PO reference for {invoice_id}")
                
                # Check if PO required for this amount
                config = await db.config.get_by_field("company_id", company_id)
                require_po_limit = config.validation_rules.require_po_above if config else 0
                
                if data.total > require_po_limit:
                    msg = "PO Reference Missing"
                    await self._update_invoice(invoice_id, InvoiceStatus.EXCEPTION, 
                                               MatchingResults(has_po=False, match_status="NO_PO", details=msg))
                    state["current_state"] = InvoiceStatus.EXCEPTION
                    state["matching_results"] = {"has_po": False, "match_status": "NO_PO", "details": msg}
                    return state
                else:
                    # Small enough to bypass PO? -> Go to Approval Routing
                    await self._update_invoice(invoice_id, InvoiceStatus.APPROVAL_ROUTING,
                                                MatchingResults(has_po=False, match_status="NO_PO_ALLOWED", auto_approvable=False))
                    state["current_state"] = InvoiceStatus.APPROVAL_ROUTING
                    state["matching_results"] = {"has_po": False, "match_status": "NO_PO_ALLOWED"}
                    return state

            # 3. Fetch PO
            po = await db.db["purchase_orders"].find_one({"po_number": po_number, "company_id": company_id})
            if not po:
                msg = f"PO {po_number} not found"
                await self._update_invoice(invoice_id, InvoiceStatus.EXCEPTION,
                                           MatchingResults(has_po=False, match_status="PO_NOT_FOUND", details=msg))
                state["current_state"] = InvoiceStatus.EXCEPTION
                return state
                
            po_obj = PurchaseOrder(**po)
            
            # 4. Fetch GRNs
            grn_cursor = db.db["goods_receipt_notes"].find({"po_number": po_number, "company_id": company_id})
            grns = [GoodsReceiptNote(**doc) for doc in await grn_cursor.to_list(100)]
            
            # 5. Perform 3-Way Match
            match_results = self._three_way_match(data, po_obj, grns, await self._get_tolerances(company_id))
            
            # 6. Determine Next State
            next_state = InvoiceStatus.APPROVAL_ROUTING
            
            if match_results.match_status == "VARIANCE":
                 # If variance is acceptable (auto-approvable logic inside _three_way_match handled this flag)
                 if match_results.auto_approvable:
                     # Skip manual approval if config allows, but usually still goes to payment prep or a light approval
                     next_state = InvoiceStatus.PAYMENT_PREPARATION
                 else:
                     # Needs specific approval for variance
                     next_state = InvoiceStatus.AWAITING_APPROVAL 
            
            elif match_results.match_status == "MATCHED":
                 next_state = InvoiceStatus.PAYMENT_PREPARATION # Auto-approved effectively
            
            elif match_results.match_status == "FAILED":
                 next_state = InvoiceStatus.EXCEPTION

            # Update DB
            await self._update_invoice(invoice_id, next_state, match_results)
            
            # Update State
            state["matching_results"] = match_results.model_dump()
            state["current_state"] = next_state
            
        except Exception as e:
            logger.error(f"Matching failed: {e}")
            state["errors"] = [str(e)]
            state["current_state"] = InvoiceStatus.EXCEPTION
            
        return state

    async def _update_invoice(self, invoice_id: str, status: str, results: MatchingResults):
        await db.invoices.update(invoice_id, {
            "status": status, 
            "matching": results.model_dump()
        })

    async def _get_tolerances(self, company_id: str):
        config = await db.config.get_by_field("company_id", company_id)
        if config:
            return config.matching_tolerances
        # Defaults
        from app.models.config import MatchingTolerances
        return MatchingTolerances()

    def _three_way_match(self, invoice: InvoiceData, po: PurchaseOrder, grns: List[GoodsReceiptNote], tolerances: Any) -> MatchingResults:
        """Core logic for matching amounts and quantities."""
        
        results = MatchingResults(has_po=True, match_status="MATCHED", auto_approvable=True)
        details = []
        is_variance = False
        is_fail = False
        
        # 1. Total Amount Check
        # Compare Invoice Total vs PO Total (Note: PO might have multiple invoices, so we should check remaining balance ideally)
        # For simplicity, we compare Invoice Total vs (Sum of GRN matched items or PO line totals)
        # Let's verify Unit Prices matches first (Invoice Unit Price vs PO Unit Price)
        
        # We need to map invoice lines to PO lines. Assuming description or product code match? 
        # Or simplistic: check total invoice amount vs PO amount expected for those quantities.
        
        # Simple Aggregation Approach:
        # Expected Total = Sum(Invoice Qty * PO Unit Price)
        # Actual Total = Invoice Total
        
        # Build Item Map from PO
        po_items_map = {item.description: item.unit_price for item in po.line_items} # Description as key is risky but common in MVP
        
        calc_expected_total = 0.0
        
        for item in invoice.line_items:
            expected_price = po_items_map.get(item.description)
            if expected_price is None:
                # Item not on PO?
                # Try fuzzy? Or just fail
                # For now, assume if not found, it's a variance
                pass
            else:
                # Price Variance Check
                price_diff_percent = abs(item.unit_price - expected_price) / expected_price * 100
                if price_diff_percent > tolerances.price_variance_percent:
                    is_variance = True
                    details.append(f"Price variance on {item.description}: {price_diff_percent:.2f}%")
            
            # Check GRN Quantity
            # Sum quantity received for this item from all GRNs
            qty_received = sum(
                grn_item.quantity 
                for grn in grns 
                for grn_item in grn.line_items 
                if grn_item.description == item.description
            )
            
            # Quantity Variance Check
            # Invoice Qty vs Received Qty
            if item.quantity > qty_received:
                # Invoiced for more than received?
                is_variance = True
                details.append(f"Qty variance on {item.description}: Invoiced {item.quantity}, Received {qty_received}")
                
            calc_expected_total += item.quantity * (expected_price if expected_price else item.unit_price)

        # Total Variance Check
        total_diff = abs(invoice.total - po.total) # Simple Invoice vs PO check? 
        # Better: Invoice Total vs Calculated Expected Total (based on PO prices)
        
        total_diff_abs = abs(invoice.subtotal - calc_expected_total)
        if total_diff_abs > tolerances.total_amount_variance: # e.g. £1.00
             # Is it a big percentage?
             pass

        if is_variance:
            results.match_status = "VARIANCE"
            results.auto_approvable = False # Be strict for now
            results.details = "; ".join(details)
            results.price_variance = 0.0 # Fill real calc
            results.quantity_variance = 0.0 # Fill real calc

        return results

matching_agent = MatchingAgent()
