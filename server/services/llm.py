"""
ExamGuard Pro - Local LLM Service
Uses Ollama for advanced cheating detection and text reasoning
"""
import httpx
import json
import os
from typing import Dict, Any, Optional

class localLLMService:
    def __init__(self, model="llama3"):
        self.base_url = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
        self.model = model
        self.enabled = False
        
    async def check_connection(self) -> bool:
        """Check if Ollama is running"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.base_url.replace("/generate", "/tags"), timeout=2.0)
                if response.status_code == 200:
                    self.enabled = True
                    return True
        except Exception:
            self.enabled = False
        return False

    async def analyze_behavior(self, text: str, violations: list) -> Dict[str, Any]:
        """
        Use LLM to determine if the behavior is suspicious
        """
        if not self.enabled and not await self.check_connection():
            return {"status": "skipped", "reason": "Ollama not running"}

        prompt = f"""
        Analyze the following student activity for potential cheating in an exam.
        Extracted Text from Screen: {text}
        Detected Violations: {', '.join(violations)}
        
        Task: Determine if this behavior indicates meaningful cheating or just casual browsing.
        Return your answer in JSON format:
        {{
            "is_cheating": boolean,
            "confidence": float (0-1),
            "reasoning": "string",
            "risk_level": "low/medium/high"
        }}
        """

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.base_url,
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "format": "json"
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return json.loads(result.get("response", "{}"))
        except Exception as e:
            return {"status": "error", "message": str(e)}
        
        return {"status": "error", "message": "Failed to get response from LLM"}

# Singleton instance
llm_service = localLLMService()

def get_llm_service():
    return llm_service
