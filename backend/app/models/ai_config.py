import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime
from backend.app.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class AIConfig(Base):
    __tablename__ = "ai_configs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), unique=True, nullable=False, index=True)
    provider = Column(String(50), nullable=False)  # deepseek, anthropic, google, groq, ollama, openai, openrouter
    model = Column(String(100), nullable=False)
    temperature = Column(Float, default=0.0)
    max_tokens = Column(Integer, default=16000)
    reasoning_mode = Column(Boolean, default=False)
    structured_output = Column(Boolean, default=True)
    use_vision = Column(String(20), default="auto")  # auto, never, always
    fallback_model = Column(String(100), nullable=True)
    timeout_seconds = Column(Integer, default=90)
    retry_count = Column(Integer, default=3)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
