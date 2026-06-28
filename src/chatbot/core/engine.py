import json
import logging
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from django.conf import settings

from chatbot.core.ai_providers import get_ai_provider, AIMessage, AIResponse
from chatbot.core.tool_registry import get_tool_registry
from chatbot.core.domain_loader import get_all_domain_repositories


logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    response: str
    tools_used: List[str]
    tool_calls_count: int
    error: Optional[str] = None


class FunctionCallingEngine:
    
    def __init__(self):
        self.ai_provider = get_ai_provider()
        self.tool_registry = get_tool_registry()
        self.repositories = get_all_domain_repositories()
        
        # Get configuration
        chatbot_config = settings.CHATBOT_CONFIG
        self.max_tool_calls = chatbot_config.get('MAX_TOOL_CALLS_PER_QUESTION', 5)
        self.temperature = chatbot_config.get('AI_TEMPERATURE', 0.0)
        
        logger.info(
            f"FunctionCallingEngine initialized: "
            f"provider={chatbot_config.get('AI_PROVIDER')}, "
            f"max_calls={self.max_tool_calls}"
        )
    
    def execute_query(
        self,
        user_message: str,
        conversation_history: Optional[List[AIMessage]] = None
    ) -> ExecutionResult:
        start_time = time.time()
        
        messages = conversation_history.copy() if conversation_history else []
        messages.append(AIMessage(role='user', content=user_message))
        
        tools_used = []
        tool_calls_count = 0
        
        provider_name = settings.CHATBOT_CONFIG.get('AI_PROVIDER', 'openai')
        tool_definitions = self.tool_registry.get_tool_definitions_for_ai(provider_name)
        
        logger.info(
            f"Starting query execution: user_message='{user_message[:50]}...', "
            f"available_tools={len(tool_definitions)}"
        )
        
        iteration = 0
        while iteration < self.max_tool_calls:
            iteration += 1
            iteration_start = time.time()
            
            logger.info(f"Iteration {iteration}/{self.max_tool_calls}")
            
            try:
                ai_start = time.time()
                ai_response = self.ai_provider.chat_completion(
                    messages=messages,
                    tools=tool_definitions,
                    temperature=self.temperature
                )
                ai_duration = time.time() - ai_start
                logger.info(f"⏱️ AI Provider call took {ai_duration:.2f}s")
                
                if ai_response.has_tool_calls:
                    logger.info(f"AI requested {len(ai_response.tool_calls)} tool calls")
                    
                    if tool_calls_count + len(ai_response.tool_calls) > self.max_tool_calls:
                        logger.warning(f"Tool call limit reached: {self.max_tool_calls}")
                        return ExecutionResult(
                            response="Desculpe, atingi o limite de consultas para esta pergunta. Por favor, reformule sua pergunta de forma mais específica.",
                            tools_used=tools_used,
                            tool_calls_count=tool_calls_count,
                            error="MAX_TOOL_CALLS_EXCEEDED"
                        )
                    
                    messages.append(AIMessage(
                        role='assistant',
                        content=ai_response.content,
                        tool_calls=ai_response.tool_calls
                    ))
                    
                    for tool_call in ai_response.tool_calls:
                        tool_name = tool_call['name']
                        tool_id = tool_call['id']
                        
                        logger.info(f"Executing tool: {tool_name}")
                        logger.info(
                            f"AUDIT: tool_execution, "
                            f"tool={tool_name}, "
                            f"iteration={iteration}, "
                            f"total_calls={tool_calls_count + 1}"
                        )
                        
                        tools_used.append(tool_name)
                        tool_calls_count += 1
                        
                        try:
                            tool_start = time.time()
                            tool_result = self._execute_tool(tool_name, tool_call['arguments'])
                            tool_duration = time.time() - tool_start
                            result_content = json.dumps(tool_result, ensure_ascii=False)
                            
                            logger.info(f"⏱️ Tool {tool_name} executed in {tool_duration:.2f}s")
                            
                        except Exception as e:
                            logger.error(f"Tool {tool_name} execution failed: {e}")
                            result_content = json.dumps({
                                'error': str(e),
                                'tool': tool_name
                            })
                        
                        messages.append(AIMessage(
                            role='tool',
                            content=result_content,
                            tool_call_id=tool_id,
                            name=tool_name
                        ))
                    
                    iteration_duration = time.time() - iteration_start
                    logger.info(f"⏱️ Iteration {iteration} completed in {iteration_duration:.2f}s")
                    
                    continue
                
                else:
                    total_duration = time.time() - start_time
                    logger.info(f"✅ AI provided final response. Total time: {total_duration:.2f}s")
                    
                    return ExecutionResult(
                        response=ai_response.content or "Desculpe, não consegui gerar uma resposta.",
                        tools_used=tools_used,
                        tool_calls_count=tool_calls_count
                    )
            
            except Exception as e:
                logger.error(f"Error in iteration {iteration}: {e}", exc_info=True)
                return ExecutionResult(
                    response=f"Desculpe, ocorreu um erro ao processar sua pergunta: {str(e)}",
                    tools_used=tools_used,
                    tool_calls_count=tool_calls_count,
                    error=str(e)
                )
        
        logger.warning(f"Max iterations reached: {self.max_tool_calls}")
        return ExecutionResult(
            response="Desculpe, não consegui completar sua solicitação dentro do limite de iterações. Por favor, tente uma pergunta mais específica.",
            tools_used=tools_used,
            tool_calls_count=tool_calls_count,
            error="MAX_ITERATIONS_REACHED"
        )
    
    def _execute_tool(self, tool_name: str, arguments_json: str) -> Dict[str, Any]:
        tool = self.tool_registry.get_tool(tool_name)
        if not tool:
            raise ValueError(f"Tool '{tool_name}' not found in registry")
        
        try:
            arguments = json.loads(arguments_json)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON arguments: {e}")
        
        # Get the first available domain repository
        if not self.repositories:
            raise ValueError("No domain repositories available")
        
        # Get the first repository (works with single or multiple domains)
        repository = next(iter(self.repositories.values()))
        
        try:
            result = tool.execute(repository, **arguments)
            return result
        except Exception as e:
            logger.error(f"Tool execution error: {e}", exc_info=True)
            raise ValueError(f"Tool execution failed: {str(e)}")
