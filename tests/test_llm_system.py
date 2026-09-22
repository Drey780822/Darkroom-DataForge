import pytest
from pydantic import BaseModel
from backend.app.llm.registry import ModelRegistry
from backend.app.llm.schemas import (
    ModelMetadata,
    ProviderConfig,
    DocumentUnderstandingResponse,
    SchemaInferenceResponse,
)
from backend.app.llm.providers.openai_compatible import extract_json_from_text
from backend.app.llm.router import LLMRouter, EscalationLevel, ExtractionMode

class SampleSchema(BaseModel):
    saqa_id: str
    qualification_name: str
    nqf_level: int

def test_model_registry_providers_and_models():
    providers = ModelRegistry.list_providers()
    assert len(providers) >= 6
    provider_ids = [p.id for p in providers]
    assert "deepseek" in provider_ids
    assert "ollama" in provider_ids
    assert "google" in provider_ids
    assert "anthropic" in provider_ids
    assert "groq" in provider_ids
    assert "openai" in provider_ids

    models = ModelRegistry.list_models()
    assert len(models) >= 10
    deepseek_models = [m.model for m in models if m.provider == "deepseek"]
    assert "deepseek-reasoner" in deepseek_models
    assert "deepseek-chat" in deepseek_models

def test_extract_json_from_text():
    raw_markdown = """Here is the extracted data:
```json
{
  "saqa_id": "118792",
  "qualification_name": "AI Software Developer",
  "nqf_level": 5
}
```
Hope this helps!"""
    cleaned = extract_json_from_text(raw_markdown)
    parsed = SampleSchema.model_validate_json(cleaned)
    assert parsed.saqa_id == "118792"
    assert parsed.qualification_name == "AI Software Developer"
    assert parsed.nqf_level == 5

def test_credential_storage_and_masking():
    ModelRegistry.set_credential("ollama", base_url="http://localhost:11434")
    cred = ModelRegistry.get_credential("ollama")
    assert cred["base_url"] == "http://localhost:11434"

def test_llm_router_provider_resolution():
    ollama_provider = LLMRouter.get_provider("ollama")
    assert ollama_provider.provider_id == "ollama"

    deepseek_provider = LLMRouter.get_provider("deepseek")
    assert deepseek_provider.provider_id == "deepseek"
