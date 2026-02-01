import logging
import uuid
import collections
from datetime import datetime
from typing import List, Optional, Dict, Any, Union
import json
from enum import Enum

from app.database import db
from app.models.audit import AuditEvent, Action, Actor, Decision, ActionType
from app.models.invoice import Invoice

# ReportLab Imports
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet

logger = logging.getLogger(__name__)

class AuditLogger:
    def __init__(self):
        # We assume db is a global/singleton we can access or pass in
        pass

    async def log_event(self, 
                        invoice_id: str, 
                        event_type: Union[str, ActionType], 
                        actor: Dict[str, Any], 
                        action_details: str, 
                        metadata: Dict[str, Any] = None):
        """
        Generic logging point.
        """
        if not metadata:
            metadata = {}
            
        company_id = metadata.get("company_id")
        if not company_id:
            # Try to fetch from invoice if not provided?
            # For speed, assume caller passes or we fetch lightly
            # Let's default if missing for now, or require it
            company_id = "unknown" 

        # Construct Actor model
        if isinstance(actor, dict):
             actor_obj = Actor(**actor)
        else:
             actor_obj = actor # valid if Pydantic model
             
        # ActionType
        if isinstance(event_type, str):
            # Try mapping
            try:
                e_type = ActionType(event_type)
            except:
                e_type = ActionType.USER_ACTION # Fallback
        else:
            e_type = event_type
            
        event = AuditEvent(
            event_id=f"EVT-{uuid.uuid4().hex}",
            invoice_id=invoice_id,
            company_id=company_id,
            timestamp=datetime.utcnow(),
            actor=actor_obj,
            action=Action(
                action_type=e_type,
                performed_by=actor_obj,
                details=action_details,
                timestamp=datetime.utcnow(),
                metadata=metadata
            ),
            related_entities=metadata.get("related", {})
        )
        
        # Save to DB via existing simple repo or direct
        if db.audit:
            await db.audit.create(event)
        else:
            logger.warning("Audit DB not available, skipping log save.")
            
        logger.info(f"AUDIT [{e_type}]: {action_details} ({invoice_id})")

    async def log_decision(self,
                           invoice_id: str,
                           made_by: str,
                           reasoning: str,
                           options: List[str],
                           chosen: str,
                           confidence: float = 1.0,
                           metadata: Dict[str, Any] = None):
        """
        Log an agent decision explicitly.
        """
        company_id = (metadata or {}).get("company_id", "unknown")
        
        actor = Actor(id=made_by, name=made_by, type="AGENT")
        
        decision = Decision(
            made_by=made_by,
            reasoning=reasoning,
            options_considered=options,
            chosen_option=chosen,
            confidence=confidence,
            metadata=metadata or {}
        )
        
        event = AuditEvent(
            event_id=f"EVT-{uuid.uuid4().hex}",
            invoice_id=invoice_id,
            company_id=company_id,
            actor=actor,
            action=Action(
                action_type=ActionType.AGENT_DECISION,
                performed_by=actor,
                details=f"Decision: {chosen}. {reasoning}",
                metadata={"confidence": confidence}
            ),
            decision=decision
        )
        
        if db.audit:
            await db.audit.create(event)
            
    async def log_state_transition(self, invoice_id: str, from_state: str, to_state: str, company_id: str = None):
        if not company_id:
            # Ideally fetch
            company_id = "unknown"
            
        actor = Actor(id="workflow_engine", name="Workflow", type="SYSTEM")
        
        await self.log_event(
            invoice_id=invoice_id,
            event_type=ActionType.STATE_CHANGE,
            actor=actor.model_dump(),
            action_details=f"State changed from {from_state} to {to_state}",
            metadata={"company_id": company_id}
        )

    async def get_audit_trail(self, invoice_id: str) -> List[AuditEvent]:
        if not db.audit:
            return []
        # sort by timestamp
        query = {"invoice_id": invoice_id}
        cursor = db.db["audit_events"].find(query).sort("timestamp", 1)
        results = await cursor.to_list(None)
        return [AuditEvent(**doc) for doc in results]

    async def generate_audit_report(self, invoice_id: str, format: str = "PDF") -> str:
        """
        Generates a file and returns the path (or content bytes in real API).
        Saves locally for now.
        """
        events = await self.get_audit_trail(invoice_id)
        
        if format.upper() == "PDF":
            filename = f"audit_report_{invoice_id}.pdf"
            self._create_pdf(filename, invoice_id, events)
            return filename
        elif format.upper() == "JSON":
             filename = f"audit_report_{invoice_id}.json"
             with open(filename, "w") as f:
                 json.dump([e.model_dump(mode='json') for e in events], f, indent=2)
             return filename
        else:
            raise ValueError("Unsupported format")

    def _create_pdf(self, filename: str, invoice_id: str, events: List[AuditEvent]):
        doc = SimpleDocTemplate(filename, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        story.append(Paragraph(f"Audit Report: {invoice_id}", styles['Title']))
        story.append(Spacer(1, 12))
        
        # Table Data
        data = [["Timestamp", "Type", "Actor", "Details"]]
        
        for e in events:
            ts = e.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            etype = e.action.action_type.value
            actor = f"{e.actor.name} ({e.actor.type})"
            details = e.action.details[:100] + ("..." if len(e.action.details) > 100 else "")
            
            data.append([ts, etype, actor, details])
            
        t = Table(data, colWidths=[100, 80, 100, 250])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
        ]))
        
        story.append(t)
        doc.build(story)

audit_logger = AuditLogger()
