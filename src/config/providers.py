"""LLM provider configurations for CodeSight."""

from dataclasses import dataclass, field
from typing import List


@dataclass
class OllamaConfig:
    """Ollama local LLM configuration."""
    base_url: str = "http://localhost:11434"
    model: str = "llama3.1:70b"
    timeout: int = 300


@dataclass
class OpenAIConfig:
    """OpenAI API configuration."""
    api_key: str = ""
    model: str = "gpt-4"
    timeout: int = 300


@dataclass
class KongAWSConfig:
    """Kong Gateway AWS Bedrock configuration."""
    base_url: str = "https://api-pub.dev.developer.nbcuni.com/aigateway/aws"
    model: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"
    available_models: List[str] = field(default_factory=lambda: [
        "anthropic.claude-3-5-sonnet-20241022-v2:0",
        "anthropic.claude-3-5-haiku-20241022-v1:0",
        "anthropic.claude-3-opus-20240229-v1:0",
        "amazon.titan-text-express-v1",
        "cohere.command-text-v14",
        "ai21.j2-ultra-v1",
        "meta.llama2-70b-chat-v1",
        "mistral.mistral-7b-instruct-v0:2"
    ])
    timeout: int = 300
    max_retries: int = 3
    retry_delay: float = 1.0


@dataclass
class KongAzureConfig:
    """Kong Gateway Azure OpenAI configuration."""
    base_url: str = "https://api-pub.dev.developer.nbcuni.com/aigateway/azure"
    model: str = "gpt-4o"
    available_models: List[str] = field(default_factory=lambda: [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-3.5-turbo",
        "text-embedding-ada-002"
    ])
    timeout: int = 300
    max_retries: int = 3
    retry_delay: float = 1.0


@dataclass  
class KongGCPConfig:
    """Kong Gateway Google Cloud AI configuration."""
    base_url: str = "https://api-pub.dev.developer.nbcuni.com/aigateway/gcp"
    model: str = "gemini-1.5-pro-002"
    available_models: List[str] = field(default_factory=lambda: [
        "gemini-1.5-pro-002",
        "gemini-1.5-flash-002",
        "text-bison-001"
    ])
    timeout: int = 300
    max_retries: int = 3
    retry_delay: float = 1.0


@dataclass
class LLMConfig:
    """Complete LLM configuration with all providers."""
    provider: str = "kong_aws"
    temperature: float = 0.1
    max_tokens: int = 4000
    top_p: float = 0.9
    json_mode: bool = True
    citation_required: bool = True
    abstain_min_confidence: float = 0.5
    
    # Provider configurations
    ollama: OllamaConfig = field(default_factory=OllamaConfig)
    openai: OpenAIConfig = field(default_factory=OpenAIConfig)
    kong_aws: KongAWSConfig = field(default_factory=KongAWSConfig)
    kong_azure: KongAzureConfig = field(default_factory=KongAzureConfig)
    kong_gcp: KongGCPConfig = field(default_factory=KongGCPConfig)
    
    @property
    def model(self) -> str:
        """Get the model for the current provider."""
        provider_config = getattr(self, self.provider, None)
        if provider_config and hasattr(provider_config, 'model'):
            return str(provider_config.model)
        return ""
    
    @model.setter
    def model(self, value: str) -> None:
        """Set the model for the current provider."""
        provider_config = getattr(self, self.provider, None)
        if provider_config and hasattr(provider_config, 'model'):
            provider_config.model = value
