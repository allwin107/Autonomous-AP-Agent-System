import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from app.database import db
from app.models.invoice import Invoice, InvoiceStatus
from app.models.memory import Memory, MemoryType
from app.memory.semantic_memory import semantic_memory
from app.tools.groq_llm import groq_tool

logger = logging.getLogger(__name__)

class ReflectionAgent:
    """
    Analyzes invoice processing outcomes to extract patterns and improve future performance.
    """
    
    async def reflect_on_failure(self, invoice_id: str, failure_type: str, context: Optional[str] = None):
        """
        Triggered when a workflow fails (Exception, Timeout, etc.)
        """
        logger.info(f"Reflecting on failure for invoice {invoice_id}. Type: {failure_type}")
        
        # 1. Fetch Context
        invoice = await db.invoices.get_by_field("invoice_id", invoice_id)
        if not invoice:
            return
            
        audit_logs = await db.audit.get_for_invoice(invoice_id)
        audit_summary = "\n".join([f"{e.action.timestamp}: {e.action.action_type} - {e.action.details}" for e in audit_logs])
        
        # 2. Extract Pattern via LLM
        prompt = f"""
        Analyze this invoice processing failure:
        Failure Type: {failure_type}
        Additional Context: {context or 'None'}
        
        Invoice Data:
        - Vendor: {invoice.data.vendor_name if invoice.data else 'Unknown'}
        - Amount: {invoice.data.total if invoice.data else 0.0}
        - Status: {invoice.status}
        
        Actions Taken (Audit Log):
        {audit_summary}
        
        What pattern caused this failure?
        Is this vendor-specific or generalizable?
        What should be done differently next time?
        Confidence in this assessment (0.0-1.0)?
        
        Return strictly valid JSON:
        {{
            "pattern_identified": "...",
            "is_vendor_specific": true/false,
            "recommended_action": "...",
            "confidence": 0.85
        }}
        """
        
        try:
            analysis = groq_tool.generate_structured(prompt)
            
            # 3. Store Learning if confidence is high
            if analysis.get("confidence", 0) > 0.6:
                memory = Memory(
                    type=MemoryType.ERROR,
                    observation=f"Failure {failure_type} on invoice {invoice_id}",
                    learning=f"Pattern: {analysis['pattern_identified']}. Recommended: {analysis['recommended_action']}",
                    pattern=analysis['pattern_identified'],
                    vendor_name=invoice.data.vendor_name if invoice.data else None,
                    vendor_id=invoice.data.vendor_id if invoice.data else None,
                    confidence=analysis['confidence'],
                    metadata={
                        "failure_type": failure_type,
                        "is_vendor_specific": analysis['is_vendor_specific'],
                        "audit_trail_length": len(audit_logs)
                    }
                )
                await semantic_memory.store_learning(memory)
                logger.info(f"Stored reflective learning for {invoice_id}")
                
        except Exception as e:
            logger.error(f"Reflection pattern extraction failed for {invoice_id}: {e}")

    async def reflect_on_success(self, invoice_id: str):
        """
        Analyzes smooth paths to understand what works well.
        """
        # Similar logic to failure but with focus on OPTIMIZATION
        logger.info(f"Reflecting on success for invoice {invoice_id}")
        # In a real system, we might only do this for "interesting" successes 
        # (e.g. very fast processing, complex matching that worked)
        pass

    async def apply_learnings(self, invoice: Invoice) -> List[str]:
        """
        Retrieves relevant memories to provide hints or guardrails during processing.
        """
        if not invoice.data or not invoice.data.vendor_name:
            return []
            
        query = f"Vendor: {invoice.data.vendor_name} | Processing past issues"
        memories = await semantic_memory.retrieve_similar_cases(query, limit=3, min_similarity=0.75)
        
        hints = []
        for mem in memories:
            if mem.get("confidence", 0) > 0.8:
                hints.append(f"PREVIOUS_LEARNING: {mem['learning']}")
                
        return hints

reflection_agent = ReflectionAgent()
