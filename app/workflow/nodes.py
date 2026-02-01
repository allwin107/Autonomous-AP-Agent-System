import logging
from typing import Dict, Any

from app.workflow.state import InvoiceState
from app.models.invoice import InvoiceStatus
from app.agents.ingestion import IngestionAgent # Ingestion is usually the trigger, but here if we include it in graph
from app.agents.extraction import extraction_agent
from app.agents.validation import validation_agent
from app.agents.matching import matching_agent
from app.agents.approval import approval_agent
from app.agents.payment import payment_agent
from app.agents.recording import recording_agent
from app.agents.reflection import reflection_agent

logger = logging.getLogger(__name__)

# ... existing code ...

async def recording_node(state: InvoiceState) -> InvoiceState:
    logger.info(f"Node: Accounting Recording for {state['invoice_id']}")
    res = await recording_agent.recording_node(state)
    # Trigger reflection on success
    await reflection_agent.reflect_on_success(state['invoice_id'])
    return res

# Define Node Wrappers
# These simple wrappers calling the agent's logic allow us to keep the agent code independent of LangGraph if needed
# and handle edge cases or state translation here.

async def ingestion_node(state: InvoiceState) -> InvoiceState:
    # In a real cyclic graph, this might poll or just pass through if triggered externally
    # For now, we assume graph starts AFTER ingestion or ingestion is the entry point
    return state

async def extraction_node(state: InvoiceState) -> InvoiceState:
    logger.info(f"Node: Extraction for {state['invoice_id']}")
    return await extraction_agent.extraction_node(state)

async def validation_node(state: InvoiceState) -> InvoiceState:
    logger.info(f"Node: Validation for {state['invoice_id']}")
    # Apply prior learnings before/during validation
    invoice = await db.invoices.get_by_field("invoice_id", state['invoice_id'])
    if invoice:
        hints = await reflection_agent.apply_learnings(invoice)
        if hints:
            logger.info(f"Applying {len(hints)} learning hints to {state['invoice_id']}")
            state.setdefault("flags", []).extend(hints)
            
    return await validation_agent.validation_node(state)

async def matching_node(state: InvoiceState) -> InvoiceState:
    logger.info(f"Node: Matching for {state['invoice_id']}")
    return await matching_agent.matching_node(state)

async def approval_routing_node(state: InvoiceState) -> InvoiceState:
    logger.info(f"Node: Approval Routing for {state['invoice_id']}")
    return await approval_agent.approval_routing_node(state)

async def payment_prep_node(state: InvoiceState) -> InvoiceState:
    logger.info(f"Node: Payment Prep for {state['invoice_id']}")
    return await payment_agent.payment_prep_node(state)

async def exception_handler_node(state: InvoiceState) -> InvoiceState:
    logger.error(f"Node: Exception for {state['invoice_id']}. Errors: {state.get('errors')}")
    # Logic to notify or park the invoice
    state['current_state'] = InvoiceStatus.EXCEPTION
    
    # Trigger reflection on failure
    await reflection_agent.reflect_on_failure(
        state['invoice_id'], 
        failure_type="WORKFLOW_EXCEPTION",
        context=f"Errors: {state.get('errors')}"
    )
    return state

# Node Mapping for Graph
NODES = {
    "ingestion": ingestion_node,
    "extraction": extraction_node,
    "validation": validation_node,
    "matching": matching_node,
    "approval": approval_routing_node,
    "payment": payment_prep_node,
    "exception": exception_handler_node
}
