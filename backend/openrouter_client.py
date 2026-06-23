import requests
import logging
from typing import Dict, Any

from backend.config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, OPENROUTER_MODELS

logger = logging.getLogger(__name__)


class OpenRouterClient:
    def __init__(self, api_key: str = OPENROUTER_API_KEY):
        self.api_key = api_key
        self.base_url = OPENROUTER_BASE_URL
        self.models = OPENROUTER_MODELS

    def _call_model(self, model: str, messages: list, max_tokens: int = 500) -> str:
        if not self.api_key:
            logger.warning("No OpenRouter API key set. Set OPENROUTER_API_KEY env var.")
            return None

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://newsverify.app",
            "X-Title": "NewsVerify AI",
        }

        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.1,
        }

        try:
            resp = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30,
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]
            else:
                logger.warning(f"Model {model} HTTP {resp.status_code}: {resp.text[:200]}")
                return None
        except Exception as e:
            logger.error(f"Error calling {model}: {e}")
            return None

    def generate(self, system_prompt: str, user_prompt: str, max_tokens: int = 500) -> Dict[str, Any]:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        errors = []
        for tier in ["primary", "fallback_1", "fallback_2"]:
            model = self.models[tier]
            result = self._call_model(model, messages, max_tokens)
            if result:
                logger.info(f"OpenRouter success with {tier}: {model}")
                return {"success": True, "response": result, "model": model}
            errors.append(f"{tier} ({model})")

        logger.error(f"All OpenRouter models failed: {'; '.join(errors)}")
        return {"success": False, "response": None, "model": None, "errors": errors}
