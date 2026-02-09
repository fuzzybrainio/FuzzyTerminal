from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, field_validator

class ProviderConfig(BaseModel):
    api_key: Optional[str] = None
    model: Optional[str] = None
    base_url: Optional[str] = None

class PreferencesConfig(BaseModel):
    auto_suggest: bool = True
    context_aware: bool = True
    max_suggestions: int = Field(default=3, ge=1, le=10)

class RemoteHostConfig(BaseModel):
    host: str
    user: str
    port: int = 22
    key_path: str = "~/.ssh/id_rsa"
    password: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    added_at: Optional[str] = None
    last_used: Optional[str] = None
    success_count: int = 0
    fail_count: int = 0

class FuzzyConfig(BaseModel):
    provider: str = "anthropic"
    providers: Dict[str, ProviderConfig] = Field(default_factory=dict)
    preferences: PreferencesConfig = Field(default_factory=PreferencesConfig)
    plugins: Dict[str, bool] = Field(default_factory=dict)
    remote_hosts: Dict[str, RemoteHostConfig] = Field(default_factory=dict)

    @field_validator('provider')
    def validate_provider(cls, v):
        valid_providers = ["anthropic", "ollama", "gemini", "openrouter", "grok", "openai", "deepseek"]
        if v not in valid_providers:
            raise ValueError(f"Provider must be one of {valid_providers}")
        return v
