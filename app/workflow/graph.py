from typing import Dict, Any, Literal
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from app.workflow.state import InvoiceState
from app.workflow.nodes import NODES
from app.models.invoice import InvoiceStatus

class InvoiceWorkflow:
    def __init__(self):
        self.workflow = StateGraph(InvoiceState)
        self.checkpointer = MemorySaver()
        self._build_graph()

    def _build_graph(self):
        # 1. Add Nodes
        self.workflow.add_node("ingestion", NODES["ingestion"])
        self.workflow.add_node("extraction", NODES["extraction"])
        self.workflow.add_node("validation", NODES["validation"])
        self.workflow.add_node("matching", NODES["matching"])
        self.workflow.add_node("approval", NODES["approval"])
        self.workflow.add_node("payment", NODES["payment"])
        self.workflow.add_node("exception", NODES["exception"])

        # 2. Set Entry Point
        self.workflow.set_entry_point("ingestion")

        # 3. Add Edges & Conditional Logic
        
        # Ingestion -> Extraction (Always, if valid)
        self.workflow.add_edge("ingestion", "extraction")

        # Extraction -> Validation OR Exception
        def route_extraction(state: InvoiceState) -> Literal["validation", "exception"]:
            if state["current_state"] == InvoiceStatus.EXCEPTION or state.get("errors"):
                return "exception"
            return "validation"
            
        self.workflow.add_conditional_edges(
            "extraction",
            route_extraction
        )

        # Validation -> Matching OR Exception
        def route_validation(state: InvoiceState) -> Literal["matching", "exception", "approval"]:
            if state["current_state"] == InvoiceStatus.EXCEPTION:
                return "exception"
            if state["current_state"] == InvoiceStatus.AWAITING_APPROVAL:
                 # Logic for early approval routing if needed, but usually matching first
                 pass
            
            # If validated OK, go to matching
            return "matching"

        self.workflow.add_conditional_edges(
            "validation",
            route_validation
        )

        # Matching -> Approval OR Exception
        def route_matching(state: InvoiceState) -> Literal["approval", "exception"]:
            if state["current_state"] == InvoiceStatus.EXCEPTION:
                return "exception"
            return "approval"

        self.workflow.add_conditional_edges(
            "matching",
            route_matching
        )

        # Approval -> Payment OR Exception (or Wait)
        def route_approval(state: InvoiceState) -> Literal["payment", "exception", "__end__"]:
            if state["current_state"] == InvoiceStatus.EXCEPTION:
                return "exception"
            if state["current_state"] == InvoiceStatus.AWAITING_APPROVAL:
                # End of automation, waiting for human
                return END
            return "payment"

        self.workflow.add_conditional_edges(
            "approval",
            route_approval
        )

        # Payment -> End
        self.workflow.add_edge("payment", END)
        
        # Exception -> End (for now, or human loop)
        self.workflow.add_edge("exception", END)

        # 4. Compile
        self.app = self.workflow.compile(checkpointer=self.checkpointer)

    def get_runnable(self):
        return self.app
    
    def get_graph_image(self):
        """Export mermaid png"""
        return self.app.get_graph().draw_mermaid_png()

invoice_workflow = InvoiceWorkflow()
