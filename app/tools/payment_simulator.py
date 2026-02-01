import logging
import uuid
import random
from typing import List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class PaymentSimulator:
    """
    Simulates integration with a banking system (e.g. Lloyds, Barclays, Stripe).
    Generates dummy files and simulates processing delays.
    """
    def __init__(self):
        self._payments = {} # In-memory store for simulation results

    def generate_bacs_file(self, payment_instructions: List[Dict[str, Any]]) -> str:
        """
        Generates a mock BACS (Standard 18) file content.
        """
        # Standard 18 format simulation (Vol 1 Header, Vol 2 Data etc.)
        # Simplified: CSV or Fixed Width representation
        
        lines = ["VOL1000000", "HDR1A000000"]
        for instr in payment_instructions:
            # SortCode, Account, Amount (pence), Ref, Name
            sort = instr.get("sort_code", "").replace("-", "")
            acc = instr.get("account_number", "")
            amount_pence = int(instr.get("amount", 0.0) * 100)
            ref = instr.get("reference", "INV")
            name = instr.get("payee_name", "")[:18]
            
            line = f"{sort:6}{acc:8}099{amount_pence:011}{ref:18}{name:18}"
            lines.append(line)
            
        lines.append("EOF1A000000")
        return "\n".join(lines)

    async def simulate_payment_processing(self, payment_id: str) -> bool:
        """
        Simulate async processing. Returns success/fail.
        """
        # In real life, this might call an API.
        logger.info(f"Simulating payment processing for {payment_id}")
        
        # 95% Success rate
        is_success = random.random() > 0.05
        
        self._payments[payment_id] = {
            "status": "PROCESSED" if is_success else "FAILED",
            "timestamp": datetime.utcnow()
        }
        return is_success

    def check_payment_status(self, payment_id: str) -> str:
        if payment_id in self._payments:
            return self._payments[payment_id]["status"]
        return "UNKNOWN"

payment_simulator = PaymentSimulator()
