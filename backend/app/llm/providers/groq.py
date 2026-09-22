from backend.app.llm.providers.openai_compatible import OpenAICompatibleProvider
from backend.app.llm.registry import ModelRegistry

class GroqProvider(OpenAICompatibleProvider):
    """Groq Cloud provider with ultra-low latency LPU inference."""

    def __init__(self, provider_id: str = "groq", api_key: str = None, base_url: str = None):
        super().__init__(provider_id, api_key, base_url)
        if not self.base_url:
            cred = ModelRegistry.get_credential("groq")
            self.base_url = cred.get("base_url") or "https://api.groq.com/openai/v1"
        if not self.api_key:
            cred = ModelRegistry.get_credential("groq")
            self.api_key = cred.get("api_key", "")
