import json
import logging
import time
from typing import Any, Dict, List, Optional

import httpx
from django.conf import settings
from google import genai
from google.genai import errors, types

from .base import AIMessage, AIProvider, AIResponse


logger = logging.getLogger(__name__)


class GeminiProvider(AIProvider):
    """Google Gemini provider using the supported google-genai SDK."""

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-3.6-flash",
        timeout: int = 90,
        max_retries: int = 3,
    ):
        super().__init__(api_key, model, timeout, max_retries)
        self.client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=timeout * 1000),
        )

    def _validate_credentials(self) -> None:
        if not self.api_key or len(self.api_key.strip()) < 20:
            raise ValueError("Invalid Google API key format")

    def chat_completion(
        self,
        messages: List[AIMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.0,
    ) -> AIResponse:
        contents = self._format_messages(messages)
        gemini_tools = self.format_tool_definitions(tools or [])
        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=4096,
            system_instruction=settings.CHATBOT_CONFIG.get("SYSTEM_INSTRUCTION"),
            tools=gemini_tools or None,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )

        for attempt in range(self.max_retries):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=contents,
                    config=config,
                )
                tool_calls = self.parse_tool_calls(response)
                content = None if tool_calls else (response.text or None)
                return AIResponse(
                    content=content,
                    tool_calls=tool_calls,
                    finish_reason="tool_calls" if tool_calls else "stop",
                    provider_content=(
                        response.candidates[0].content
                        if response.candidates
                        else None
                    ),
                )
            except errors.APIError as exc:
                retryable = exc.code in {429, 500, 502, 503, 504}
                if not retryable or attempt == self.max_retries - 1:
                    raise RuntimeError("Gemini request failed") from exc
                wait_time = self._exponential_backoff(attempt)
                logger.warning(
                    "Gemini temporary error (status=%s). Retrying in %.1fs",
                    exc.code,
                    wait_time,
                )
                time.sleep(wait_time)
            except httpx.TimeoutException as exc:
                if attempt == self.max_retries - 1:
                    raise RuntimeError("Gemini request timed out") from exc
                wait_time = self._exponential_backoff(attempt)
                logger.warning(
                    "Gemini request timed out. Retrying in %.1fs",
                    wait_time,
                )
                time.sleep(wait_time)

        raise RuntimeError("Gemini request failed after all retries")

    def format_tool_definitions(self, tools: List[Dict[str, Any]]) -> List[types.Tool]:
        declarations = []
        for tool in tools:
            function = tool.get("function", tool)
            declarations.append(
                types.FunctionDeclaration(
                    name=function["name"],
                    description=function["description"],
                    parameters_json_schema=function["parameters"],
                )
            )
        return [types.Tool(function_declarations=declarations)] if declarations else []

    def parse_tool_calls(self, response: Any) -> Optional[List[Dict[str, Any]]]:
        function_calls = response.function_calls or []
        tool_calls = [
            {
                "id": function_call.id or f"gemini_{index}_{int(time.time() * 1000)}",
                "name": function_call.name,
                "arguments": json.dumps(dict(function_call.args or {}), ensure_ascii=False),
            }
            for index, function_call in enumerate(function_calls)
        ]
        return tool_calls or None

    def _format_messages(self, messages: List[AIMessage]) -> List[types.Content]:
        contents: List[types.Content] = []

        for message in messages:
            # Gemini 3 returns thought signatures with function calls. Reusing
            # the original content preserves those signatures and call IDs for
            # the next model turn.
            if message.role == "assistant" and message.provider_content is not None:
                contents.append(message.provider_content)
                continue

            if message.role == "tool":
                try:
                    result = json.loads(message.content)
                except json.JSONDecodeError:
                    result = {"result": message.content}
                contents.append(
                    types.Content(
                        # Gemini treats a custom function response as a user
                        # turn, not as a separate "tool" role.
                        role="user",
                        parts=[
                            types.Part(
                                function_response=types.FunctionResponse(
                                    id=message.tool_call_id,
                                    name=message.name or "unknown_tool",
                                    response=result,
                                )
                            )
                        ],
                    )
                )
                continue

            role = "model" if message.role == "assistant" else "user"
            parts = []
            if message.content:
                parts.append(types.Part.from_text(text=message.content))
            for tool_call in message.tool_calls or []:
                parts.append(
                    types.Part.from_function_call(
                        name=tool_call["name"],
                        args=json.loads(tool_call["arguments"]),
                    )
                )
            if parts:
                contents.append(types.Content(role=role, parts=parts))

        return contents
