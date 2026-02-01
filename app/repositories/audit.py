from app.repositories.base import BaseRepository
from app.models.audit import AuditEvent, Action, Actor, ActionType

class AuditLogger(BaseRepository[AuditEvent]):
    
    async def log_event(self, event: AuditEvent):
        """Log an event to the audit trail."""
        await self.create(event)

    async def log_action(self, 
                         company_id: str, 
                         actor: Actor, 
                         action_type: ActionType, 
                         details: str, 
                         invoice_id: str = None):
        """Helper to quickly log an action."""
        import uuid
        from datetime import datetime
        
        event = AuditEvent(
            event_id=f"EVT-{uuid.uuid4()}",
            invoice_id=invoice_id,
            company_id=company_id,
            actor=actor,
            action=Action(
                action_type=action_type,
                performed_by=actor,
                details=details,
                timestamp=datetime.utcnow()
            )
        )
        await self.create(event)
