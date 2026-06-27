from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class AIMessage:
    role: str
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None


@dataclass
class AIResponse:
    content: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    finish_reason: str = "stop"
    
    @property
    def has_tool_calls(self) -> bool:
        return self.tool_calls is not None and len(self.tool_calls) > 0


class AIProvider(ABC):
    
    def __init__(self, api_key: str, model: str, timeout: int = 30, max_retries: int = 3):
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        self._validate_credentials()
    
    @abstractmethod
    def _validate_credentials(self) -> None:
        pass
    
    @abstractmethod
    def chat_completion(
        self,
        messages: List[AIMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7
    ) -> AIResponse:
        pass
    
    @abstractmethod
    def format_tool_definitions(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        pass
    
    @abstractmethod
    def parse_tool_calls(self, response: Any) -> Optional[List[Dict[str, Any]]]:
        pass
    
    def _exponential_backoff(self, attempt: int) -> float:
        base_wait = 1.0
        return base_wait * (2 ** attempt)
