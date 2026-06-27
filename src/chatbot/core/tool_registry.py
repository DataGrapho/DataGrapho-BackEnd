from typing import Dict, List, Optional
import re

from chatbot.core.base_tool import Tool


class ToolRegistry:
    
    def __init__(self):
        self._tools: Dict[str, Tool] = {}
    
    def register_tool(self, tool: Tool) -> None:
        self._validate_tool_definition(tool)
        
        if tool.name in self._tools:
            raise ValueError(f"Tool with name '{tool.name}' already registered")
        
        self._tools[tool.name] = tool
    
    def get_tool(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)
    
    def get_all_tools(self) -> List[Tool]:
        return list(self._tools.values())
    
    def get_tool_definitions_for_ai(self, provider: str) -> List[Dict]:
        provider_upper = provider.upper()
        
        if provider_upper in ('OPENAI', 'GEMINI'):
            return [tool.to_openai_format() for tool in self._tools.values()]
        elif provider_upper == 'ANTHROPIC':
            return [tool.to_anthropic_format() for tool in self._tools.values()]
        else:
            raise ValueError(f"Unsupported AI provider: {provider}")
    
    def _validate_tool_definition(self, tool: Tool) -> None:
        if not tool.name:
            raise ValueError("Tool name cannot be empty")
        
        if len(tool.name) > 50:
            raise ValueError("Tool name must be 50 characters or less")
        
        if not re.match(r'^[a-z][a-z0-9_]*$', tool.name):
            raise ValueError(
                "Tool name must start with lowercase letter and contain only "
                "lowercase letters, numbers, and underscores"
            )
        
        if not tool.description:
            raise ValueError("Tool description cannot be empty")
        
        if len(tool.description) > 500:
            raise ValueError("Tool description must be 500 characters or less")
        
        if not isinstance(tool.parameters, dict):
            raise ValueError("Tool parameters must be a dictionary")
        
        valid_types = {'string', 'integer', 'float', 'date', 'boolean'}
        for param_name, param_type in tool.parameters.items():
            if not re.match(r'^[a-z][a-z0-9_]*$', param_name):
                raise ValueError(
                    f"Parameter name '{param_name}' must start with lowercase letter "
                    "and contain only lowercase letters, numbers, and underscores"
                )
            
            if param_type not in valid_types:
                raise ValueError(
                    f"Parameter type '{param_type}' is not supported. "
                    f"Valid types: {valid_types}"
                )
        
        if tool.query_template:
            for param_name in tool.parameters.keys():
                placeholder = f"{{{param_name}}}"
                if placeholder not in tool.query_template:
                    raise ValueError(
                        f"Parameter '{param_name}' not found in query template"
                    )


_registry = ToolRegistry()


def get_tool_registry() -> ToolRegistry:
    return _registry
