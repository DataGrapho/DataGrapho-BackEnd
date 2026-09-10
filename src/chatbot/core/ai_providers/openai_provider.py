import time
import logging
from typing import List, Dict, Any, Optional

from django.conf import settings

from openai import OpenAI, APIError, RateLimitError, APITimeoutError

from .base import AIProvider, AIMessage, AIResponse


logger = logging.getLogger(__name__)


class OpenAIProvider(AIProvider):
    
    def __init__(self, api_key: str, model: str = "gpt-4o-mini", timeout: int = 30, max_retries: int = 3, base_url: Optional[str] = None):
        self.base_url = base_url
        super().__init__(api_key, model, timeout, max_retries)
        
        client_kwargs = {
            "api_key": api_key,
            "timeout": timeout
        }
        if base_url:
            client_kwargs["base_url"] = base_url
            logger.info(f"Using custom base URL: {base_url}")
        
        self.client = OpenAI(**client_kwargs)
    
    def _validate_credentials(self) -> None:
        if self.base_url:
            logger.info("Skipping API key validation for custom base URL")
            return
        
        if not self.api_key or not self.api_key.startswith('sk-'):
            raise ValueError("Invalid OpenAI API key format")
    
    def chat_completion(
        self,
        messages: List[AIMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7
    ) -> AIResponse:
        system_prompt = {
            "role": "system",
            "content": (
                "Você é um assistente financeiro com acesso a um banco de dados. "
                "Você TEM ferramentas disponíveis e DEVE usá-las para responder perguntas sobre dados.\n\n"
                
                "REGRAS OBRIGATÓRIAS:\n"
                "1. Se o usuário perguntar sobre clientes, receitas ou despesas, você DEVE usar as ferramentas\n"
                "2. NUNCA diga que não tem acesso aos dados - você TEM acesso através das ferramentas\n"
                "3. NUNCA invente dados - sempre use as ferramentas para buscar informações reais\n"
                "4. Se não souber qual ferramenta usar, use a que parecer mais apropriada\n\n"
                
                "Ferramentas disponíveis:\n"
                "- get_top_customers: Use quando perguntarem sobre principais clientes\n"
                "- get_revenue_by_period: Use quando perguntarem sobre receitas\n"
                "- get_expenses_by_category: Use quando perguntarem sobre despesas\n"
                "- compare_periods: Use quando perguntarem para comparar períodos\n\n"
                
                "Formato de resposta:\n"
                "- Use R$ para valores monetários (ex: R$ 150.000,00)\n"
                "- Use datas em português (ex: 'janeiro de 2024')\n"
                "- Seja claro e objetivo"
            )
        }
        
        system_prompt["content"] = settings.CHATBOT_CONFIG.get("SYSTEM_INSTRUCTION")
        openai_messages = [system_prompt] + self._format_messages(messages)
        
        request_params = {
            "model": self.model,
            "messages": openai_messages,
            "temperature": temperature
        }
        
        if tools:
            request_params["tools"] = self.format_tool_definitions(tools)
            request_params["tool_choice"] = "auto"
            logger.info(f"📋 Sending {len(tools)} tools to AI: {[t.get('function', {}).get('name', t.get('name')) for t in tools]}")
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"OpenAI request attempt {attempt + 1}/{self.max_retries}")
                
                response = self.client.chat.completions.create(**request_params)
                
                message = response.choices[0].message
                finish_reason = response.choices[0].finish_reason
                tool_calls = self.parse_tool_calls(message)
                content = message.content if message.content else None
                
                logger.info(f"✅ OpenAI response received: finish_reason={finish_reason}, has_tools={tool_calls is not None}, tool_count={len(tool_calls) if tool_calls else 0}")
                
                if tool_calls:
                    logger.info(f"🔧 Tools requested by AI: {[tc['name'] for tc in tool_calls]}")
                else:
                    logger.info(f"💬 AI provided text response (no tools): {content[:100] if content else 'None'}...")
                
                return AIResponse(
                    content=content,
                    tool_calls=tool_calls,
                    finish_reason=finish_reason
                )
                
            except RateLimitError as e:
                logger.warning(f"OpenAI rate limit hit on attempt {attempt + 1}: {e}")
                if attempt < self.max_retries - 1:
                    wait_time = self._exponential_backoff(attempt)
                    logger.info(f"Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                else:
                    raise Exception(f"OpenAI rate limit exceeded after {self.max_retries} attempts") from e
                    
            except APITimeoutError as e:
                logger.warning(f"OpenAI timeout on attempt {attempt + 1}: {e}")
                if attempt < self.max_retries - 1:
                    wait_time = self._exponential_backoff(attempt)
                    logger.info(f"Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                else:
                    raise Exception(f"OpenAI timeout after {self.max_retries} attempts") from e
                    
            except APIError as e:
                logger.error(f"OpenAI API error on attempt {attempt + 1}: {e}")
                if attempt < self.max_retries - 1:
                    wait_time = self._exponential_backoff(attempt)
                    logger.info(f"Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                else:
                    raise Exception(f"OpenAI API error after {self.max_retries} attempts") from e
        
        raise Exception("OpenAI request failed after all retries")
    
    def format_tool_definitions(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        openai_tools = []
        
        for tool in tools:
            if "type" in tool and tool["type"] == "function" and "function" in tool:
                openai_tools.append(tool)
            else:
                openai_tool = {
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool["description"],
                        "parameters": tool["parameters"]
                    }
                }
                openai_tools.append(openai_tool)
        
        return openai_tools
    
    def parse_tool_calls(self, message: Any) -> Optional[List[Dict[str, Any]]]:
        if not hasattr(message, 'tool_calls') or not message.tool_calls:
            return None
        
        tool_calls = []
        for tool_call in message.tool_calls:
            tool_calls.append({
                "id": tool_call.id,
                "name": tool_call.function.name,
                "arguments": tool_call.function.arguments
            })
        
        return tool_calls
    
    def _format_messages(self, messages: List[AIMessage]) -> List[Dict[str, Any]]:
        openai_messages = []
        
        for msg in messages:
            if msg.role == "tool":
                openai_messages.append({
                    "role": "tool",
                    "tool_call_id": msg.tool_call_id,
                    "name": msg.name,
                    "content": msg.content
                })
            elif msg.tool_calls:
                tool_calls = []
                for tc in msg.tool_calls:
                    tool_calls.append({
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": tc["arguments"]
                        }
                    })
                openai_messages.append({
                    "role": "assistant",
                    "content": msg.content,
                    "tool_calls": tool_calls
                })
            else:
                openai_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
        
        return openai_messages
