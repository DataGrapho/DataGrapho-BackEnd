import logging
from typing import Optional
from django.conf import settings

from .base import AIProvider, AIMessage, AIResponse
from .openai_provider import OpenAIProvider
from .anthropic_provider import AnthropicProvider
from .gemini_provider import GeminiProvider


logger = logging.getLogger(__name__)


DEFAULT_MODELS = {
    'openai': 'gpt-4o-mini',
    'anthropic': 'claude-3-5-sonnet-20241022',
    'gemini': 'gemini-2.0-flash'
}


def get_ai_provider() -> AIProvider:
    chatbot_config = getattr(settings, 'CHATBOT_CONFIG', {})
    
    provider_name = chatbot_config.get('AI_PROVIDER', '').lower()
    api_key = chatbot_config.get('AI_API_KEY', '')
    model = chatbot_config.get('AI_MODEL', '')
    
    if not provider_name:
        raise ValueError("AI_PROVIDER not configured in environment variables")
    
    if not api_key:
        raise ValueError("AI_API_KEY not configured in environment variables")
    
    # Use default model if not specified
    if not model:
        model = DEFAULT_MODELS.get(provider_name)
        if not model:
            raise ValueError(f"No default model for provider: {provider_name}")
    
    timeout = chatbot_config.get('AI_TIMEOUT', 30)
    max_retries = chatbot_config.get('AI_MAX_RETRIES', 3)
    base_url = chatbot_config.get('AI_BASE_URL', None)
    
    if provider_name == 'openai':
        logger.info(f"Initializing OpenAI provider with model: {model}")
        if base_url:
            logger.info(f"Using custom base URL: {base_url}")
        return OpenAIProvider(
            api_key=api_key,
            model=model,
            timeout=timeout,
            max_retries=max_retries,
            base_url=base_url
        )
    
    elif provider_name == 'anthropic':
        logger.info(f"Initializing Anthropic provider with model: {model}")
        return AnthropicProvider(
            api_key=api_key,
            model=model,
            timeout=timeout,
            max_retries=max_retries
        )
    
    elif provider_name == 'gemini':
        logger.info(f"Initializing Gemini provider with model: {model}")
        return GeminiProvider(
            api_key=api_key,
            model=model,
            timeout=timeout,
            max_retries=max_retries
        )
    
    else:
        raise ValueError(
            f"Unsupported AI provider: {provider_name}. "
            f"Supported: 'openai', 'anthropic', 'gemini'"
        )


__all__ = [
    'AIProvider',
    'AIMessage',
    'AIResponse',
    'OpenAIProvider',
    'AnthropicProvider',
    'GeminiProvider',
    'get_ai_provider'
]
