import logging
from typing import Dict, Any

from app.workflow.state import InvoiceState
from app.models.invoice import InvoiceStatus
from app.agents.ingestion import IngestionAgent # Ingestion is usually the trigger, but here if we include it in graph
from app.agents.extraction import extraction_agent
from app.agents.validation import validation_agent
from app.agents.matching import matching_agent

logger = logging.getLogger(__name__)

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
    return await validation_agent.validation_node(state)

async def matching_node(state: InvoiceState) -> InvoiceState:
    logger.info(f"Node: Matching for {state['invoice_id']}")
    return await matching_agent.matching_node(state)

async def approval_routing_node(state: InvoiceState) -> InvoiceState:
    logger.info(f"Node: Approval Routing for {state['invoice_id']}")
    # Determine who needs to approve
    # For demo, if risk > 0.5 or high value, requires human
    # Set next state
    if state.get('risk_score', 0) > 0.5 or state.get('human_approval_required'):
        state['current_state'] = InvoiceStatus.AWAITING_APPROVAL
    else:
        state['current_state'] = InvoiceStatus.PAYMENT_PREPARATION
    return state

async def payment_prep_node(state: InvoiceState) -> InvoiceState:
    logger.info(f"Node: Payment Prep for {state['invoice_id']}")
    state['current_state'] = InvoiceStatus.PAYMENT_SCHEDULED
    # Generate payment instruction
    return state

async def exception_handler_node(state: InvoiceState) -> InvoiceState:
    logger.error(f"Node: Exception for {state['invoice_id']}. Errors: {state.get('errors')}")
    # Logic to notify or park the invoice
    state['current_state'] = InvoiceStatus.EXCEPTION
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
