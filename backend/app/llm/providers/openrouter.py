from backend.app.llm.providers.openai_compatible import OpenAICompatibleProvider
from backend.app.llm.registry import ModelRegistry

class OpenRouterProvider(OpenAICompatibleProvider):
    """OpenRouter universal API provider."""

    def __init__(self, provider_id: str = "openrouter", api_key: str = None, base_url: str = None):
        super().__init__(provider_id, api_key, base_url)
        if not self.base_url:
            cred = ModelRegistry.get_credential("openrouter")
            self.base_url = cred.get("base_url") or "https://openrouter.ai/api/v1"
        if not self.api_key:
            cred = ModelRegistry.get_credential("openrouter")
            self.api_key = cred.get("api_key", "")

    def _get_headers(self) -> dict:
        headers = super()._get_headers()
        headers["HTTP-Referer"] = "https://darkroom-dataforge.wits.ac.za"
        headers["X-Title"] = "Wits-merSETA Darkroom DataForge"
        return headers
