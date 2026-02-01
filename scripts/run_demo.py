import asyncio
import argparse
import sys
from app.workflow.graph import app as workflow
from app.database import db

async def run_scenario(scenario_name: str):
    print(f"--- Running Scenario: {scenario_name} ---")
    # This script triggers the actual workflow for various scenarios
    # For demo purposes, we trigger the LangGraph orchestration
    
    # Example state for demo
    sample_state = {
        "invoice_id": "INV-DEMO-001",
        "company_id": "acme_corp",
        "current_state": "INGESTION",
        "errors": []
    }
    
    print(f"Invoking LangGraph for {sample_state['invoice_id']}...")
    try:
        # Note: In a real run, this would be triggered by a file upload or email
        result = await workflow.ainvoke(sample_state, config={"configurable": {"thread_id": "demo-thread"}})
        print(f"Result Status: {result.get('current_state')}")
        print("Success! Check the Monitoring Dashboard at http://localhost:8000/ui/monitoring")
    except Exception as e:
        print(f"Error running scenario: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run AI AP Employee Demo Scenarios")
    parser.add_argument("--scenario", type=str, default="all", help="Scenario to run (1-7 or all)")
    args = parser.parse_args()
    
    db.connect()
    try:
        asyncio.run(run_scenario(args.scenario))
    finally:
        db.close()
