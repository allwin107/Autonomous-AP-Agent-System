import json
import logging
from typing import Dict, Any, List, Optional
from groq import Groq
from app.config import settings

logger = logging.getLogger(__name__)

class GroqLLMTool:
    def __init__(self):
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.model = "llama-3.1-70b-versatile" 

    def generate_structured(self, prompt: str, schema: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate a structured JSON response from the LLM.
        If schema is provided, we can rely on JSON mode.
        """
        messages = [
            {
                "role": "system",
                "content": "You are a specialized AI assistant that extracts structured invoice data. Output strictly valid JSON."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]

        try:
            # For Groq, we ensure JSON mode is explicitly requested if supported or reliable via prompting
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.0,
                response_format={"type": "json_object"}
            )
            
            content = completion.choices[0].message.content
            return json.loads(content)
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            raise

    def make_decision(self, context: str, options: List[str]) -> str:
        """
        Ask LLM to choose the best option from a list based on context.
        """
        prompt = f"""
        Context: {context}
        
        Options:
        {options}
        
        Return strictly valid JSON with field 'choice' matching one of the options options exactly.
        """
        result = self.generate_structured(prompt)
        return result.get("choice", "")

groq_tool = GroqLLMTool()
