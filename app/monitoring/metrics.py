import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from app.database import db
from app.models.invoice import InvoiceStatus

logger = logging.getLogger(__name__)

class ObservabilityMetrics:
    def __init__(self):
        pass

    async def get_system_health(self, company_id: str) -> Dict[str, Any]:
        """
        Aggregate overall system health metrics.
        """
        now = datetime.utcnow()
        day_ago = now - timedelta(days=1)
        
        # 1. Pipeline Status Breakdown
        pipeline = [
            {"$match": {"company_id": company_id}},
            {"$group": {"_id": "$status", "count": {"$sum": 1}}}
        ]
        status_counts = await db.invoices.collection.aggregate(pipeline).to_list(length=None)
        status_map = {item["_id"]: item["count"] for item in status_counts}

        # 2. Success/Failure in last 24h
        period_pipeline = [
            {"$match": {
                "company_id": company_id,
                "updated_at": {"$gte": day_ago}
            }},
            {"$group": {
                "_id": None,
                "total": {"$sum": 1},
                "exceptions": {"$sum": {"$cond": [{"$eq": ["$status", InvoiceStatus.EXCEPTION]}, 1, 0]}},
                "paid": {"$sum": {"$cond": [{"$eq": ["$status", InvoiceStatus.PAID]}, 1, 0]}}
            }}
        ]
        results = await db.invoices.collection.aggregate(period_pipeline).to_list(length=None)
        period_stats = results[0] if results else {"total": 0, "exceptions": 0, "paid": 0}

        success_rate = 0.0
        if period_stats["total"] > 0:
            # Simple success rate: (Total - Exceptions) / Total
            success_rate = ((period_stats["total"] - period_stats["exceptions"]) / period_stats["total"]) * 100

        return {
            "status_distribution": status_map,
            "last_24h": {
                "total_processed": period_stats["total"],
                "success_rate": round(success_rate, 2),
                "exception_count": period_stats["exceptions"]
            },
            "total_invoices": sum(status_map.values()),
            "active_exceptions": status_map.get(InvoiceStatus.EXCEPTION, 0)
        }

    async def get_agent_performance(self, agent_id: str, company_id: str) -> Dict[str, Any]:
        """
        Calculates success rate and latency for a specific agent from audit logs.
        """
        # Look for AGENT_DECISION or SYSTEM_EVENT performed by this agent
        pipeline = [
            {"$match": {
                "company_id": company_id,
                "actor.id": agent_id,
                "action.action_type": {"$in": ["AGENT_DECISION", "SYSTEM_EVENT", "STATE_CHANGE"]}
            }},
            {"$group": {
                "_id": "$action.success",
                "count": {"$sum": 1}
            }}
        ]
        results = await db.audit.collection.aggregate(pipeline).to_list(length=None)
        
        success_count = 0
        failure_count = 0
        for res in results:
            if res["_id"] is True:
                success_count = res["count"]
            else:
                failure_count = res["count"]

        total = success_count + failure_count
        success_rate = (success_count / total * 100) if total > 0 else 0.0

        return {
            "agent_id": agent_id,
            "total_actions": total,
            "success_rate": round(success_rate, 2),
            "failure_count": failure_count
        }

    async def get_cost_metrics(self, company_id: str) -> Dict[str, Any]:
        """
        Track LLM costs. For MVP, we estimate based on extraction counts.
        Assuming $0.01 per successful extraction for demo purposes.
        """
        count = await db.invoices.count({"company_id": company_id, "status": {"$ne": InvoiceStatus.INGESTION}})
        estimated_cost = count * 0.01 # Mock cost factor
        
        return {
            "total_estimated_cost": round(estimated_cost, 2),
            "currency": "USD",
            "extraction_count": count
        }

    async def get_sla_compliance(self, company_id: str) -> Dict[str, Any]:
        """
        Return SLA distribution.
        """
        pipeline = [
            {"$match": {"company_id": company_id}},
            {"$group": {"_id": "$sla_status", "count": {"$sum": 1}}}
        ]
        results = await db.invoices.collection.aggregate(pipeline).to_list(length=None)
        
        # Ensure we return 0 for missing categories
        compliance_map = {
            "COMPLIANT": 0,
            "AT_RISK": 0,
            "BREACHED": 0
        }
        for item in results:
            if item["_id"] in compliance_map:
                compliance_map[item["_id"]] = item["count"]

        return compliance_map

    async def get_fraud_metrics(self, company_id: str) -> Dict[str, Any]:
        """
        Return count of fraud alerts.
        """
        high_risk_count = await db.invoices.count({
            "company_id": company_id,
            "validation.fraud_score": {"$gt": 0.7}
        })
        
        flag_pipeline = [
            {"$match": {"company_id": company_id}},
            {"$unwind": "$validation.flags"},
            {"$group": {"_id": "$validation.flags", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 5}
        ]
        top_flags = await db.invoices.collection.aggregate(flag_pipeline).to_list(length=None)

        return {
            "high_risk_invoices": high_risk_count,
            "top_risk_flags": {item["_id"]: item["count"] for item in top_flags}
        }

metrics_engine = ObservabilityMetrics()
