import json
import logging
import tiktoken
from typing import Dict, Any, List, Optional
from app.database import db
from app.memory.semantic_memory import semantic_memory
from app.tools.groq_llm import groq_tool

logger = logging.getLogger(__name__)

class ContextManager:
    """
    Manages LLM context window by prioritizing, summarizing, and retrieving relevant info.
    """
    def __init__(self, model_name: str = "gpt-4o"):
        self.max_total_tokens = 4000
        self.response_reserve = 1000
        self.max_context_tokens = self.max_total_tokens - self.response_reserve
        
        try:
            self.encoding = tiktoken.encoding_for_model(model_name)
        except Exception:
            self.encoding = tiktoken.get_encoding("cl100k_base")
            
        self._cache = {}

    def estimate_tokens(self, data: Any) -> int:
        """Precisely estimate tokens for a given object using tiktoken."""
        if isinstance(data, str):
            text = data
        else:
            text = json.dumps(data, default=str)
        return len(self.encoding.encode(text))

    async def get_relevant_policies(self, task: str) -> List[str]:
        """Fetches task-specific rules or policies from DB."""
        # For simplicity, we search in a 'policies' collection or similar
        # If not exists, return defaults
        return ["Standard UK VAT rate is 20%", "Net total must match sum of line items"]

    async def get_similar_cases(self, invoice: Any, limit: int = 3) -> List[Dict[str, Any]]:
        """Retrieves similar past cases from semantic memory."""
        query = f"Issue related to {invoice.data.vendor_name if hasattr(invoice, 'data') and invoice.data else 'invoice'}"
        return await semantic_memory.retrieve_similar_cases(query, limit=limit)

    async def prepare_context_for_llm(self, state: Dict[str, Any], task_description: str) -> str:
        """
        Orchestrates prioritization and truncation to fit within token limits.
        """
        invoice_id = state.get("invoice_id")
        
        # 1. Essential Information (Always Include)
        essential = {
            "invoice_id": invoice_id,
            "current_state": state.get("current_state"),
            "task": task_description,
            "extracted_data": state.get("extracted_data"),
            "raw_text": state.get("raw_text") # Critical for extraction
        }
        
        context_parts = [
            "# ESSENTIAL CONTEXT",
            json.dumps(essential, indent=2)
        ]
        
        current_tokens = self.estimate_tokens("\n".join(context_parts))
        
        # 2. Task-Specific Data
        task_data = {}
        if "VALIDATION" in task_description.upper():
            task_data["rules"] = await self.get_relevant_policies("VALIDATION")
        
        if task_data:
            part = f"\n# TASK-SPECIFIC DATA\n{json.dumps(task_data, indent=2)}"
            part_tokens = self.estimate_tokens(part)
            if current_tokens + part_tokens < self.max_context_tokens:
                context_parts.append(part)
                current_tokens += part_tokens

        # 3. Optional: Patterns & Memories
        # Only try if we have space
        if current_tokens < self.max_context_tokens - 200:
            memories = await self.get_similar_cases(state.get("invoice"), limit=2)
            if memories:
                part = f"\n# SIMILAR PAST CASES\n{json.dumps(memories, indent=2)}"
                part_tokens = self.estimate_tokens(part)
                if current_tokens + part_tokens < self.max_context_tokens:
                    context_parts.append(part)
                    current_tokens += part_tokens
        
        # 4. Final Safety Truncation / Summarization
        final_context = "\n".join(context_parts)
        actual_tokens = self.estimate_tokens(final_context)
        if actual_tokens > self.max_context_tokens:
            logger.warning(f"Context over limit ({actual_tokens}/{self.max_context_tokens}). Summarizing.")
            return await self.summarize_context(final_context)

            
        return final_context

    async def summarize_context(self, context: str) -> str:
        """Uses LLM to compress a large context window."""
        prompt = f"Summarize the following technical context concisely while preserving all key identifiers and error messages:\n\n{context}"
        # We use the raw generate here to avoid recursive context management
        result = groq_tool.client.chat.completions.create(
            model=groq_tool.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500
        )
        return result.choices[0].message.content

context_manager = ContextManager()
