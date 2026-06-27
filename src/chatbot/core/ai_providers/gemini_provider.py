import time
import json
import logging
from typing import List, Dict, Any, Optional

import google.generativeai as genai
from google.api_core import exceptions as google_exceptions

from .base import AIProvider, AIMessage, AIResponse


logger = logging.getLogger(__name__)


class GeminiProvider(AIProvider):
    
    def __init__(self, api_key: str, model: str = "gemini-1.5-flash", timeout: int = 30, max_retries: int = 3):
        super().__init__(api_key, model, timeout, max_retries)
        
        genai.configure(api_key=api_key)
        
        self.client = genai.GenerativeModel(
            model_name=model,
            generation_config={
                'temperature': 0.0,
                'top_p': 0.95,
                'top_k': 40,
                'max_output_tokens': 8192,
            }
        )
    
    def _validate_credentials(self) -> None:
        if not self.api_key or len(self.api_key) < 20:
            raise ValueError("Invalid Google API key format")
    
    def chat_completion(
        self,
        messages: List[AIMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7
    ) -> AIResponse:
        system_instruction = (
            "Você é um assistente financeiro inteligente. "
            "Ao apresentar valores monetários, sempre use o símbolo R$ e separadores de milhares (ex: R$ 150.000,00). "
            "Ao apresentar datas, use formato legível em português (ex: 'janeiro de 2024', '15 de março'). "
            "Seja claro, objetivo e profissional nas respostas. "
            "Se precisar de múltiplas ferramentas para responder, use-as em sequência."
        )
        
        gemini_messages = self._format_messages(messages)
        
        generation_config = genai.GenerationConfig(
            temperature=temperature,
            top_p=0.95,
            top_k=40,
            max_output_tokens=8192,
        )
        
        model = genai.GenerativeModel(
            model_name=self.model,
            generation_config=generation_config,
            system_instruction=system_instruction
        )
        
        gemini_tools = None
        if tools:
            gemini_tools = self.format_tool_definitions(tools)
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Gemini request attempt {attempt + 1}/{self.max_retries}")
                
                history = []
                for i, msg in enumerate(gemini_messages[:-1]):
                    history.append(msg)
                
                chat = model.start_chat(history=history)
                
                last_message = gemini_messages[-1]['parts'][0]
                
                if gemini_tools:
                    response = chat.send_message(last_message, tools=gemini_tools)
                else:
                    response = chat.send_message(last_message)
                
                tool_calls = self.parse_tool_calls(response)
                
                content = None
                try:
                    if not tool_calls and response.text:
                        content = response.text
                except ValueError:
                    pass
                
                finish_reason = "stop"
                if tool_calls:
                    finish_reason = "tool_calls"
                
                logger.info(f"Gemini response received: finish_reason={finish_reason}, has_tools={tool_calls is not None}")
                
                return AIResponse(
                    content=content,
                    tool_calls=tool_calls,
                    finish_reason=finish_reason
                )
                
            except google_exceptions.ResourceExhausted as e:
                logger.warning(f"Gemini rate limit hit on attempt {attempt + 1}: {e}")
                if attempt < self.max_retries - 1:
                    wait_time = self._exponential_backoff(attempt)
                    logger.info(f"Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                else:
                    raise Exception(f"Gemini rate limit exceeded after {self.max_retries} attempts") from e
                    
            except google_exceptions.DeadlineExceeded as e:
                logger.warning(f"Gemini timeout on attempt {attempt + 1}: {e}")
                if attempt < self.max_retries - 1:
                    wait_time = self._exponential_backoff(attempt)
                    logger.info(f"Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                else:
                    raise Exception(f"Gemini timeout after {self.max_retries} attempts") from e
                    
            except Exception as e:
                logger.error(f"Gemini API error on attempt {attempt + 1}: {e}")
                if attempt < self.max_retries - 1:
                    wait_time = self._exponential_backoff(attempt)
                    logger.info(f"Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                else:
                    raise Exception(f"Gemini API error after {self.max_retries} attempts") from e
        
        raise Exception("Gemini request failed after all retries")
    
    def format_tool_definitions(self, tools: List[Dict[str, Any]]) -> List:
        gemini_functions = []
        
        for tool in tools:
            function = tool.get('function', {})
            name = function.get('name', '')
            description = function.get('description', '')
            parameters_schema = function.get('parameters', {})
            properties = parameters_schema.get('properties', {})
            required = parameters_schema.get('required', [])
            
            gemini_properties = {}
            
            for param_name, param_schema in properties.items():
                json_type = param_schema.get('type', 'string')
                type_mapping = {
                    'string': 'STRING',
                    'integer': 'INTEGER',
                    'number': 'NUMBER',
                    'boolean': 'BOOLEAN'
                }
                
                gemini_type = type_mapping.get(json_type, 'STRING')
                
                gemini_properties[param_name] = {
                    'type': gemini_type,
                    'description': param_schema.get('description', f'Parameter {param_name}')
                }
            
            function_declaration = genai.protos.FunctionDeclaration(
                name=name,
                description=description,
                parameters=genai.protos.Schema(
                    type=genai.protos.Type.OBJECT,
                    properties={
                        name: genai.protos.Schema(
                            type=getattr(genai.protos.Type, prop['type']),
                            description=prop['description']
                        )
                        for name, prop in gemini_properties.items()
                    },
                    required=required
                )
            )
            
            gemini_functions.append(function_declaration)
        
        return [genai.protos.Tool(function_declarations=gemini_functions)]
    
    def parse_tool_calls(self, response: Any) -> Optional[List[Dict[str, Any]]]:
        if not hasattr(response, 'candidates') or not response.candidates:
            return None
        
        candidate = response.candidates[0]
        
        if not hasattr(candidate.content, 'parts'):
            return None
        
        tool_calls = []
        
        for part in candidate.content.parts:
            if hasattr(part, 'function_call') and part.function_call:
                func_call = part.function_call
                
                args_dict = {}
                if hasattr(func_call, 'args') and func_call.args:
                    for key, value in func_call.args.items():
                        args_dict[key] = value
                
                tool_calls.append({
                    'id': f"call_{func_call.name}_{int(time.time())}",
                    'name': func_call.name,
                    'arguments': json.dumps(args_dict, ensure_ascii=False)
                })
        
        return tool_calls if tool_calls else None
    
    def _format_messages(self, messages: List[AIMessage]) -> List[Dict[str, Any]]:
        gemini_messages = []
        
        for msg in messages:
            if msg.role == "user":
                gemini_messages.append({
                    'role': 'user',
                    'parts': [msg.content]
                })
            elif msg.role == "assistant":
                if msg.tool_calls:
                    if msg.content:
                        gemini_messages.append({
                            'role': 'model',
                            'parts': [msg.content]
                        })
                else:
                    gemini_messages.append({
                        'role': 'model',
                        'parts': [msg.content]
                    })
            elif msg.role == "tool":
                gemini_messages.append({
                    'role': 'function',
                    'parts': [{
                        'function_response': {
                            'name': msg.name,
                            'response': {'result': msg.content}
                        }
                    }]
                })
        
        return gemini_messages
