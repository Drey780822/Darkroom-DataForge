import time
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.ai_config import AIConfig
from backend.app.llm.registry import ModelRegistry
from backend.app.llm.router import LLMRouter
from backend.app.llm.schemas import (
    ProviderConfig,
    ModelMetadata,
    AIModelConfigSchema,
    UpdateCredentialsRequest,
    TestConnectionRequest,
    TestConnectionResponse,
)

router = APIRouter(prefix="/ai-models", tags=["AI Models & Intelligence"])

@router.get("/providers", response_model=List[ProviderConfig])
def list_providers():
    """List all supported AI providers and their configuration status."""
    return ModelRegistry.list_providers()

@router.get("/available", response_model=List[ModelMetadata])
def list_available_models():
    """List all available models from the catalog, including dynamically detected local Ollama models."""
    return ModelRegistry.list_models()

@router.post("/credentials", status_code=status.HTTP_200_OK)
def update_credentials(payload: UpdateCredentialsRequest):
    """Securely store API keys or base URLs server-side only. Never exposed to browser."""
    ModelRegistry.set_credential(
        provider=payload.provider,
        api_key=payload.api_key,
        base_url=payload.base_url,
    )
    return {"status": "success", "message": f"Credentials for {payload.provider} updated securely on server."}

@router.post("/test-connection", response_model=TestConnectionResponse)
def test_connection(payload: TestConnectionRequest):
    """Ping a provider API or local Ollama endpoint to verify connectivity and credentials."""
    try:
        # If client provided transient credentials to test
        if payload.api_key or payload.base_url:
            ModelRegistry.set_credential(payload.provider, payload.api_key, payload.base_url)

        provider = LLMRouter.get_provider(payload.provider)
        success, msg, latency = provider.test_connection(model=payload.model)
        return TestConnectionResponse(
            success=success,
            message=msg,
            latency_ms=latency,
            provider=payload.provider,
            model=payload.model,
        )
    except Exception as e:
        return TestConnectionResponse(
            success=False,
            message=str(e),
            latency_ms=0,
            provider=payload.provider,
            model=payload.model,
        )

@router.get("/configs", response_model=List[AIModelConfigSchema])
def list_named_configs(db: Session = Depends(get_db)):
    """List custom named configurations (e.g. 'DeepSeek High Accuracy', 'Local Qwen')."""
    configs = db.query(AIConfig).order_by(AIConfig.created_at.desc()).all()
    # Seed default configs if table is empty
    if not configs:
        defaults = [
            AIConfig(
                name="DeepSeek High Accuracy",
                provider="deepseek",
                model="deepseek-reasoner",
                temperature=0.0,
                max_tokens=16000,
                reasoning_mode=True,
                structured_output=True,
                use_vision="auto",
                fallback_model="deepseek-chat",
                is_default=True,
            ),
            AIConfig(
                name="Local Qwen (Confidential)",
                provider="ollama",
                model="qwen2.5",
                temperature=0.0,
                max_tokens=8000,
                reasoning_mode=False,
                structured_output=True,
                use_vision="never",
                is_default=False,
            ),
            AIConfig(
                name="Claude Research",
                provider="anthropic",
                model="claude-3-7-sonnet-20250219",
                temperature=0.0,
                max_tokens=16000,
                reasoning_mode=True,
                structured_output=True,
                use_vision="auto",
                is_default=False,
            ),
            AIConfig(
                name="Fast Extraction (Groq)",
                provider="groq",
                model="llama-3.3-70b-versatile",
                temperature=0.0,
                max_tokens=8000,
                reasoning_mode=False,
                structured_output=True,
                use_vision="never",
                is_default=False,
            ),
        ]
        db.add_all(defaults)
        db.commit()
        configs = db.query(AIConfig).all()

    return [
        AIModelConfigSchema(
            id=c.id,
            name=c.name,
            provider=c.provider,
            model=c.model,
            temperature=c.temperature,
            max_tokens=c.max_tokens,
            reasoning_mode=c.reasoning_mode,
            structured_output=c.structured_output,
            use_vision=c.use_vision,
            fallback_model=c.fallback_model,
            timeout_seconds=c.timeout_seconds,
            retry_count=c.retry_count,
            is_default=c.is_default,
        )
        for c in configs
    ]

@router.post("/configs", response_model=AIModelConfigSchema, status_code=status.HTTP_201_CREATED)
def create_or_update_config(payload: AIModelConfigSchema, db: Session = Depends(get_db)):
    """Create or update a named AI model configuration preset."""
    existing = None
    if payload.id:
        existing = db.query(AIConfig).filter(AIConfig.id == payload.id).first()
    if not existing:
        existing = db.query(AIConfig).filter(AIConfig.name == payload.name).first()

    if existing:
        existing.provider = payload.provider
        existing.model = payload.model
        existing.temperature = payload.temperature
        existing.max_tokens = payload.max_tokens
        existing.reasoning_mode = payload.reasoning_mode
        existing.structured_output = payload.structured_output
        existing.use_vision = payload.use_vision
        existing.fallback_model = payload.fallback_model
        existing.timeout_seconds = payload.timeout_seconds
        existing.retry_count = payload.retry_count
        existing.is_default = payload.is_default
        db.commit()
        db.refresh(existing)
        target = existing
    else:
        new_config = AIConfig(
            name=payload.name,
            provider=payload.provider,
            model=payload.model,
            temperature=payload.temperature,
            max_tokens=payload.max_tokens,
            reasoning_mode=payload.reasoning_mode,
            structured_output=payload.structured_output,
            use_vision=payload.use_vision,
            fallback_model=payload.fallback_model,
            timeout_seconds=payload.timeout_seconds,
            retry_count=payload.retry_count,
            is_default=payload.is_default,
        )
        db.add(new_config)
        db.commit()
        db.refresh(new_config)
        target = new_config

    return AIModelConfigSchema(
        id=target.id,
        name=target.name,
        provider=target.provider,
        model=target.model,
        temperature=target.temperature,
        max_tokens=target.max_tokens,
        reasoning_mode=target.reasoning_mode,
        structured_output=target.structured_output,
        use_vision=target.use_vision,
        fallback_model=target.fallback_model,
        timeout_seconds=target.timeout_seconds,
        retry_count=target.retry_count,
        is_default=target.is_default,
    )

@router.delete("/configs/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_config(config_id: str, db: Session = Depends(get_db)):
    cfg = db.query(AIConfig).filter(AIConfig.id == config_id).first()
    if not cfg:
        raise HTTPException(status_code=404, detail="AI Configuration preset not found")
    db.delete(cfg)
    db.commit()
    return None
