import json
import logging
import re
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
        
        provider_name = settings.CHATBOT_CONFIG.get('AI_PROVIDER', 'openai')
        tool_definitions = self.tool_registry.get_tool_definitions_for_ai(provider_name)
        
        logger.info(
            f"Starting query execution: user_message='{user_message[:50]}...', "
            f"available_tools={len(tool_definitions)}"
        )

        forced_result = self._execute_forced_wine_query(user_message)
        if forced_result is not None:
            return forced_result
        
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

                    if len(ai_response.tool_calls) == 1 and successful_tool_results:
                        last_tool_name, last_tool_result = successful_tool_results[-1]
                    else:
                        last_tool_name, last_tool_result = None, None

                    if last_tool_name == 'get_wine_database_summary':
                        return ExecutionResult(
                            response=self._render_wine_summary(
                                last_tool_result, user_message
                            ),
                            tools_used=tools_used,
                            tool_calls_count=tool_calls_count,
                        )
                    if last_tool_name == 'search_wine_catalog':
                        return ExecutionResult(
                            response=self._render_wine_search_results(last_tool_result),
                            tools_used=tools_used,
                            tool_calls_count=tool_calls_count,
                        )
                    
                    continue
                
                else:
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
            arguments['source'] = self._resolve_wine_summary_source(user_message)
            logger.info(
                'Resolved wine summary source from user question: %s',
                arguments['source'],
            )
        elif tool_name == 'search_wine_catalog':
            arguments = self._sanitize_wine_search_arguments(arguments, user_message)
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

    @staticmethod
    def _resolve_wine_summary_source(user_message: str) -> str:
        """Escolhe a fonte pelo texto do usuário, sem confiar na inferência do modelo."""
        normalized = unicodedata.normalize('NFKD', str(user_message or ''))
        normalized = ''.join(
            char for char in normalized if not unicodedata.combining(char)
        ).casefold()

        all_markers = (
            'todas as fontes', 'todos os dados', 'ambas as fontes',
            'catalogo e historico', 'historico e catalogo', 'base inteira',
        )
        history_markers = (
            'historico', 'historica', 'historicos', 'consumo', 'consumidos',
        )
        catalog_markers = (
            'catalogo', 'produtos disponiveis', 'estoque atual',
        )
        if any(marker in normalized for marker in all_markers):
            return 'todos'
        if any(marker in normalized for marker in history_markers):
            return 'historico'
        if any(marker in normalized for marker in catalog_markers):
            return 'catalogo'
        return 'todos'

    def _execute_forced_wine_query(
        self, user_message: str
    ) -> Optional[ExecutionResult]:
        """Roteia intenções inequívocas para impedir respostas sem consulta ao banco."""
        message = self._normalize_plain_text(user_message)

        is_country_summary = (
            ('top ' in message and 'pais' in message and 'vinho' in message)
            or ('qual pais' in message and 'mais vinho' in message)
            or ('qual pais possui mais vinho' in message)
        )
        if is_country_summary and self.tool_registry.get_tool('get_wine_database_summary'):
            result = self._execute_tool(
                'get_wine_database_summary',
                json.dumps({'group_by': 'pais'}),
                user_message=user_message,
            )
            return ExecutionResult(
                response=self._render_wine_summary(result, user_message),
                tools_used=['get_wine_database_summary'],
                tool_calls_count=1,
            )

        multi_grape = any(marker in message for marker in (
            'mais de uma uva', 'multiplas uvas', 'varias uvas',
            'duas ou mais uvas',
        ))
        recommendation = message.startswith('recomende') and 'vinho' in message
        existence = message.startswith('existe') and 'vinho' in message
        if (
            (multi_grape or recommendation or existence)
            and self.tool_registry.get_tool('search_wine_catalog')
        ):
            limit = 30 if multi_grape else 10
            requested_count = re.search(r'\brecomende\s+(\d+)\b', message)
            if requested_count:
                limit = int(requested_count.group(1))
            elif 'recomende um vinho' in message or existence:
                limit = 1
            result = self._execute_tool(
                'search_wine_catalog',
                json.dumps({'limit': limit}),
                user_message=user_message,
            )
            return ExecutionResult(
                response=self._render_wine_search_results(result),
                tools_used=['search_wine_catalog'],
                tool_calls_count=1,
            )

        return None

    @classmethod
    def _sanitize_wine_search_arguments(
        cls, arguments: Dict[str, Any], user_message: str
    ) -> Dict[str, Any]:
        """Impede que filtros de perguntas anteriores contaminem a consulta atual."""
        sanitized = dict(arguments)
        message = cls._normalize_plain_text(user_message)

        country_terms = {
            'brasil': ('brasil', 'brasileiro', 'brasileira', 'brasileiros', 'brasileiras'),
            'argentina': ('argentina', 'argentino', 'argentina', 'argentinos', 'argentinas'),
            'chile': ('chile', 'chileno', 'chilena', 'chilenos', 'chilenas'),
            'italia': ('italia', 'italiano', 'italiana', 'italianos', 'italianas'),
            'franca': ('franca', 'frances', 'francesa', 'franceses', 'francesas'),
            'portugal': ('portugal', 'portugues', 'portuguesa', 'portugueses', 'portuguesas'),
        }
        country = cls._normalize_plain_text(sanitized.get('country', ''))
        if country:
            terms = country_terms.get(country, (country,))
            if not any(term in message for term in terms):
                sanitized.pop('country', None)

        for canonical_country, terms in country_terms.items():
            if any(term in message for term in terms):
                sanitized['country'] = {
                    'brasil': 'Brasil', 'argentina': 'Argentina', 'chile': 'Chile',
                    'italia': 'Itália', 'franca': 'França', 'portugal': 'Portugal',
                }[canonical_country]
                break

        for parameter in ('region', 'producer', 'grape'):
            value = cls._normalize_plain_text(sanitized.get(parameter, ''))
            if value and value not in message:
                sanitized.pop(parameter, None)

        style_terms = {
            'color': {
                'tinto': ('tinto', 'tintos'),
                'branco': ('branco', 'branca', 'brancos', 'brancas'),
                'rose': ('rose', 'rosado', 'rosada'),
                'espumante': ('espumante', 'espumantes'),
            },
            'sweetness': {
                'meio_seco': ('meio seco', 'meio-seco', 'semi seco', 'semi-seco'),
                'seco': ('seco', 'seca', 'secos', 'secas'),
                'suave': ('suave', 'suaves'),
                'doce': ('doce', 'doces'),
            },
        }
        for parameter, vocabulary in style_terms.items():
            value = cls._normalize_plain_text(sanitized.get(parameter, '')).replace(' ', '_')
            if value and not any(term in message for term in vocabulary.get(value, (value,))):
                sanitized.pop(parameter, None)

        for canonical_color, terms in style_terms['color'].items():
            if any(term in message for term in terms):
                sanitized['color'] = canonical_color
                break
        for canonical_sweetness, terms in style_terms['sweetness'].items():
            if any(term in message for term in terms):
                sanitized['sweetness'] = canonical_sweetness
                break

        if sanitized.get('max_price') is not None and not any(
            marker in message
            for marker in ('r$', 'reais', 'preco', 'custa', 'valor', 'ate ', 'abaixo')
        ):
            sanitized.pop('max_price', None)
        if sanitized.get('min_rating') is not None and not any(
            marker in message
            for marker in ('nota', 'avaliacao', 'avaliado', 'avaliada', 'estrela')
        ):
            sanitized.pop('min_rating', None)

        price_match = re.search(
            r'(?:ate|abaixo de|menor que|maximo(?: de)?)[^\d]{0,20}(\d+(?:[.,]\d+)?)',
            message,
        )
        if price_match:
            sanitized['max_price'] = float(price_match.group(1).replace(',', '.'))
        rating_match = re.search(
            r'(?:nota|avaliacao)[^\d]{0,25}(\d+(?:[.,]\d+)?)', message
        )
        if rating_match:
            sanitized['min_rating'] = float(rating_match.group(1).replace(',', '.'))

        sanitized['in_stock'] = any(
            marker in message for marker in ('estoque', 'disponivel', 'disponiveis')
        )

        query = cls._normalize_plain_text(sanitized.get('query', ''))
        if query and query not in message:
            sanitized.pop('query', None)

        multi_grape_markers = (
            'mais de uma uva', 'multiplas uvas', 'varias uvas',
            'duas ou mais uvas', 'blend',
        )
        if any(marker in message for marker in multi_grape_markers):
            sanitized['min_grape_varieties'] = 2
        else:
            sanitized.pop('min_grape_varieties', None)

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
    def _render_wine_summary(cls, result: Dict[str, Any], user_message: str) -> str:
        groups = result.get('groups', [])
        if not groups:
            return 'Não foram encontrados vinhos para esse agrupamento.'

        source_text = {
            'catalogo': 'somente o catálogo relacional',
            'historico': 'somente o histórico de consumo',
            'todos': 'o catálogo relacional e o histórico de consumo combinados',
        }[result['source']]
        top_match = re.search(r'\btop\s*(\d+)\b', cls._normalize_plain_text(user_message))
        if top_match:
            requested = max(1, int(top_match.group(1)))
            cutoff_index = min(requested, len(groups)) - 1
            cutoff_count = groups[cutoff_index]['quantidade_vinhos']
            selected = [
                group for group in groups
                if group['quantidade_vinhos'] >= cutoff_count
            ]
            lines = [
                f"{index}. **{group['grupo']}**: {group['quantidade_vinhos']} vinhos distintos."
                for index, group in enumerate(selected, start=1)
            ]
            tie_note = ''
            if len(selected) > requested:
                tie_note = (
                    f"\n\nForam exibidos {len(selected)} países porque houve empate "
                    f"na {requested}ª posição."
                )
            return (
                f"Considerando {source_text}, o ranking é:\n\n"
                + '\n'.join(lines)
                + tie_note
                + '\n\nRegra: cada nome de vinho é contado uma única vez por país.'
            )

        leaders = result.get('leaders', [])
        count = result.get('largest_count', 0)
        if len(leaders) > 1:
            leader_text = ', '.join(leaders[:-1]) + f' e {leaders[-1]}'
            return (
                f"Considerando {source_text}, há empate entre {leader_text}, "
                f"com {count} vinhos distintos cada. Cada nome é contado uma única vez por país."
            )
        return (
            f"Considerando {source_text}, o país com mais vinhos é **{leaders[0]}**, "
            f"com {count} nomes distintos. Cada nome é contado uma única vez por país."
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
