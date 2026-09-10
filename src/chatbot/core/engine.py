import json
import logging
import time
import unicodedata
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
    
    def __init__(self, ai_provider=None, tool_registry=None, repositories=None):
        self.ai_provider = ai_provider or get_ai_provider()
        self.tool_registry = tool_registry or get_tool_registry()
        self.repositories = repositories or get_all_domain_repositories()
        
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
        successful_tool_results = []
        grounding_retry_sent = False
        
        provider_name = settings.CHATBOT_CONFIG.get('AI_PROVIDER', 'openai')
        tool_definitions = self.tool_registry.get_tool_definitions_for_ai(provider_name)
        
        logger.info(
            f"Starting query execution: user_message='{user_message[:50]}...', "
            f"available_tools={len(tool_definitions)}"
        )

        iteration = 0
        # One extra provider turn is required to compose the final answer after
        # the last allowed tool call.
        max_iterations = self.max_tool_calls + 1
        while iteration < max_iterations:
            iteration += 1
            iteration_start = time.time()
            
            logger.info(f"Iteration {iteration}/{max_iterations}")
            
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
                        tool_calls=ai_response.tool_calls,
                        provider_content=ai_response.provider_content,
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
                            tool_result = self._execute_tool(
                                tool_name,
                                tool_call['arguments'],
                                user_message=user_message,
                            )
                            tool_duration = time.time() - tool_start
                            result_content = json.dumps(tool_result, ensure_ascii=False)
                            successful_tool_results.append((tool_name, tool_result))
                            
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
                    if (
                        not successful_tool_results
                        and self._requires_database_grounding(user_message)
                    ):
                        if grounding_retry_sent:
                            logger.warning('AI refused required database tool twice')
                            return ExecutionResult(
                                response=(
                                    'Não consegui consultar a base de vinhos para responder '
                                    'com segurança. Tente reformular a pergunta.'
                                ),
                                tools_used=tools_used,
                                tool_calls_count=tool_calls_count,
                                error='DATABASE_TOOL_REQUIRED',
                            )
                        grounding_retry_sent = True
                        messages.append(AIMessage(
                            role='user',
                            content=(
                                'Validação interna: esta pergunta exige dados persistidos. '
                                'Interprete a intenção e use agora a ferramenta de vinho mais '
                                'adequada; não responda com conhecimento próprio.'
                            ),
                        ))
                        logger.warning('Retrying because a database tool is required')
                        continue

                    total_duration = time.time() - start_time
                    logger.info(f"✅ AI provided final response. Total time: {total_duration:.2f}s")
                    
                    response = ai_response.content or "Desculpe, não consegui gerar uma resposta."
                    response = self._guard_grounded_response(
                        response, successful_tool_results
                    )
                    return ExecutionResult(
                        response=response,
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
    
    def _execute_tool(
        self,
        tool_name: str,
        arguments_json: str,
        user_message: str = '',
    ) -> Dict[str, Any]:
        tool = self.tool_registry.get_tool(tool_name)
        if not tool:
            raise ValueError(f"Tool '{tool_name}' not found in registry")
        
        try:
            arguments = json.loads(arguments_json)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON arguments: {e}")

        if tool_name == 'get_wine_database_summary':
            source = self._normalize_plain_text(arguments.get('source', 'todos'))
            arguments['source'] = source if source in {'catalogo', 'historico', 'todos'} else 'todos'
            logger.info(
                'Validated wine summary source requested by AI: %s',
                arguments['source'],
            )
        elif tool_name == 'search_wine_catalog':
            arguments = self._sanitize_wine_search_arguments(arguments)
            logger.info('Sanitized wine search arguments: %s', arguments)
        
        if not self.repositories:
            raise ValueError("No domain repositories available")

        if tool.domain:
            repository = self.repositories.get(tool.domain)
            if repository is None:
                raise ValueError(f"Repository for domain '{tool.domain}' is not available")
        elif len(self.repositories) == 1:
            repository = next(iter(self.repositories.values()))
        else:
            raise ValueError(f"Tool '{tool_name}' does not declare its domain")
        
        try:
            result = tool.execute(repository, **arguments)
            return result
        except Exception as e:
            logger.error(f"Tool execution error: {e}", exc_info=True)
            raise ValueError(f"Tool execution failed: {str(e)}")

    @classmethod
    def _sanitize_wine_search_arguments(
        cls, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Valida limites e tipos sem reinterpretar a decisão tomada pela IA."""
        allowed = {
            'query', 'country', 'region', 'producer', 'grape', 'color',
            'sweetness', 'max_price', 'min_rating', 'min_grape_varieties',
            'in_stock', 'limit',
        }
        sanitized = {key: value for key, value in arguments.items() if key in allowed}

        for parameter in ('query', 'country', 'region', 'producer', 'grape'):
            if parameter in sanitized:
                sanitized[parameter] = str(sanitized[parameter] or '').strip()

        for parameter in ('color', 'sweetness'):
            if parameter in sanitized:
                sanitized[parameter] = cls._normalize_plain_text(
                    sanitized[parameter]
                ).replace(' ', '_')

        in_stock = sanitized.get('in_stock', False)
        sanitized['in_stock'] = (
            in_stock if isinstance(in_stock, bool)
            else str(in_stock).strip().casefold() in {'true', '1', 'yes', 'sim'}
        )

        try:
            sanitized['limit'] = max(1, min(int(sanitized.get('limit', 10)), 30))
        except (TypeError, ValueError):
            sanitized['limit'] = 10

        return sanitized

    @staticmethod
    def _normalize_plain_text(value: Any) -> str:
        normalized = unicodedata.normalize('NFKD', str(value or ''))
        normalized = ''.join(
            char for char in normalized if not unicodedata.combining(char)
        )
        return ' '.join(normalized.casefold().split())

    @classmethod
    def _requires_database_grounding(cls, user_message: str) -> bool:
        """Identifica perguntas factuais sobre o domínio que não podem ser improvisadas."""
        message = cls._normalize_plain_text(user_message)
        domain_markers = (
            'vinho', 'vinhos', 'uva', 'uvas', 'safra', 'safras',
            'produtor', 'produtores', 'vinicola', 'vinicolas',
        )
        data_markers = (
            'quantos', 'quantas', 'quais', 'liste', 'listar', 'mostre', 'exiba',
            'top', 'ranking', 'mais', 'menos', 'existe', 'recomende', 'preco',
            'pais', 'paises', 'regiao', 'regioes', 'estoque', 'consumo',
            'historico', 'base', 'dados', 'catalogo', 'avaliacao',
        )
        return (
            any(marker in message for marker in domain_markers)
            and any(marker in message for marker in data_markers)
        )

    @classmethod
    def _guard_grounded_response(
        cls, response: str, tool_results: List[Any]
    ) -> str:
        if not tool_results or tool_results[-1][0] != 'search_wine_catalog':
            return response
        result = tool_results[-1][1]
        normalized_response = cls._normalize_plain_text(response)
        false_negative_markers = (
            'nao foram encontrados', 'nenhum vinho', 'nao existe vinho',
        )
        if result.get('count', 0) > 0 and any(
            marker in normalized_response for marker in false_negative_markers
        ):
            logger.warning('Replacing false-negative AI response with grounded wine list')
            return cls._render_wine_search_results(result)
        return response

    @staticmethod
    def _render_wine_search_results(result: Dict[str, Any]) -> str:
        if not result.get('wines'):
            return 'Não foram encontrados vinhos que atendam aos critérios informados.'

        lines = []
        for wine in result.get('wines', []):
            grapes = ', '.join(
                f"{item['nome']} ({item['percentual']:g}%)"
                if item.get('percentual') is not None else item['nome']
                for item in wine.get('uvas', [])
            ) or 'não informadas'
            rating = (
                f"{wine['avaliacao_media']:.1f}".replace('.', ',')
                if wine.get('avaliacao_media') is not None else 'não informada'
            )
            lines.append(
                f"- **{wine['nome']}** — produtor: {wine['produtor']}; "
                f"{wine['regiao']}, {wine['pais']}; uvas: {grapes}; "
                f"safra: {wine.get('safra') or 'não informada'}; "
                f"preço: {wine.get('preco_formatado') or 'não informado'}; "
                f"avaliação: {rating}; estoque: {wine.get('estoque', 0)}."
            )
        return (
            'A consulta encontrou os seguintes vinhos:\n\n'
            + '\n'.join(lines)
            + '\n\nOs registros marcados como demonstrativos usam valores fictícios de teste.'
        )
