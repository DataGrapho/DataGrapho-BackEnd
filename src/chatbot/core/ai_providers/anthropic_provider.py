import time
import json
import logging
from typing import List, Dict, Any, Optional

from django.conf import settings

from anthropic import Anthropic, APIError, RateLimitError, APITimeoutError

from .base import AIProvider, AIMessage, AIResponse


logger = logging.getLogger(__name__)


class AnthropicProvider(AIProvider):
    
    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022", timeout: int = 30, max_retries: int = 3):
        super().__init__(api_key, model, timeout, max_retries)
        self.client = Anthropic(api_key=api_key, timeout=timeout)
    
    def _validate_credentials(self) -> None:
        if not self.api_key or not self.api_key.startswith('sk-ant-'):
            raise ValueError("Invalid Anthropic API key format")
    
    def chat_completion(
        self,
        messages: List[AIMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7
    ) -> AIResponse:
        system_prompt = (
            "Você é um assistente financeiro inteligente. "
            "Ao apresentar valores monetários, sempre use o símbolo R$ e separadores de milhares (ex: R$ 150.000,00). "
            "Ao apresentar datas, use formato legível em português (ex: 'janeiro de 2024', '15 de março'). "
            "Seja claro, objetivo e profissional nas respostas. "
            "Se precisar de múltiplas ferramentas para responder, use-as em sequência."
        )
        
        system_prompt = settings.CHATBOT_CONFIG.get("SYSTEM_INSTRUCTION")
        anthropic_messages = self._format_messages(messages)
        
        request_params = {
            "model": self.model,
            "system": system_prompt,
            "messages": anthropic_messages,
            "temperature": temperature,
            "max_tokens": 4096
        }
        
        if tools:
            request_params["tools"] = self.format_tool_definitions(tools)
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Anthropic request attempt {attempt + 1}/{self.max_retries}")
                
                response = self.client.messages.create(**request_params)
                
                finish_reason = response.stop_reason
                tool_calls = self.parse_tool_calls(response)
                
                content = None
                for block in response.content:
                    if block.type == "text":
                        content = block.text
                        break
                
                logger.info(f"Anthropic response received: stop_reason={finish_reason}, has_tools={tool_calls is not None}")
                
                return AIResponse(
                    content=content,
                    tool_calls=tool_calls,
                    finish_reason=finish_reason
                )
                
            except RateLimitError as e:
                logger.warning(f"Anthropic rate limit hit on attempt {attempt + 1}: {e}")
                if attempt < self.max_retries - 1:
                    wait_time = self._exponential_backoff(attempt)
                    logger.info(f"Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                else:
                    raise Exception(f"Anthropic rate limit exceeded after {self.max_retries} attempts") from e
                    
            except APITimeoutError as e:
                logger.warning(f"Anthropic timeout on attempt {attempt + 1}: {e}")
                if attempt < self.max_retries - 1:
                    wait_time = self._exponential_backoff(attempt)
                    logger.info(f"Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                else:
                    raise Exception(f"Anthropic timeout after {self.max_retries} attempts") from e
                    
            except APIError as e:
                logger.error(f"Anthropic API error on attempt {attempt + 1}: {e}")
                if attempt < self.max_retries - 1:
                    wait_time = self._exponential_backoff(attempt)
                    logger.info(f"Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                else:
                    raise Exception(f"Anthropic API error after {self.max_retries} attempts") from e
        
        raise Exception("Anthropic request failed after all retries")
    
    def format_tool_definitions(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        anthropic_tools = []
        
        for tool in tools:
            anthropic_tool = {
                "name": tool["name"],
                "description": tool["description"],
                "input_schema": tool["parameters"]
            }
            anthropic_tools.append(anthropic_tool)
        
        return anthropic_tools
    
    def parse_tool_calls(self, response: Any) -> Optional[List[Dict[str, Any]]]:
        tool_calls = []
        
        for block in response.content:
            if block.type == "tool_use":
                tool_calls.append({
                    "id": block.id,
                    "name": block.name,
                    "arguments": json.dumps(block.input)
                })
        
        return tool_calls if tool_calls else None
    
    def _format_messages(self, messages: List[AIMessage]) -> List[Dict[str, Any]]:
        anthropic_messages = []
        
        for msg in messages:
            if msg.role == "tool":
                anthropic_messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": msg.tool_call_id,
                            "content": msg.content
                        }
                    ]
                })
            elif msg.tool_calls:
                content_blocks = []
                
                if msg.content:
                    content_blocks.append({
                        "type": "text",
                        "text": msg.content
                    })
                
                for tc in msg.tool_calls:
                    content_blocks.append({
                        "type": "tool_use",
                        "id": tc["id"],
                        "name": tc["name"],
                        "input": json.loads(tc["arguments"])
                    })
                
                anthropic_messages.append({
                    "role": "assistant",
                    "content": content_blocks
                })
            else:
                anthropic_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
        
        return anthropic_messages
