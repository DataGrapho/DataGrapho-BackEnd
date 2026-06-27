from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


@dataclass
class Tool:
    
    name: str
    description: str
    parameters: Dict[str, str]
    query_template: Optional[str] = None
    
    def validate_parameters(self, params: Dict[str, Any]) -> bool:
        for param_name in self.parameters.keys():
            if param_name not in params:
                return False
        
        for param_name in params.keys():
            if param_name not in self.parameters:
                return False
        
        return True
    
    def to_openai_format(self) -> Dict[str, Any]:
        properties = {}
        required = []
        
        for param_name, param_type in self.parameters.items():
            json_type = {
                'string': 'string',
                'integer': 'integer',
                'float': 'number',
                'date': 'string',
                'boolean': 'boolean'
            }.get(param_type, 'string')
            
            properties[param_name] = {'type': json_type}
            
            if param_type == 'date':
                properties[param_name]['format'] = 'date'
            
            required.append(param_name)
        
        return {
            'type': 'function',
            'function': {
                'name': self.name,
                'description': self.description,
                'parameters': {
                    'type': 'object',
                    'properties': properties,
                    'required': required
                }
            }
        }
    
    def to_anthropic_format(self) -> Dict[str, Any]:
        properties = {}
        required = []
        
        for param_name, param_type in self.parameters.items():
            json_type = {
                'string': 'string',
                'integer': 'integer',
                'float': 'number',
                'date': 'string',
                'boolean': 'boolean'
            }.get(param_type, 'string')
            
            properties[param_name] = {'type': json_type}
            
            if param_type == 'date':
                properties[param_name]['format'] = 'date'
            
            required.append(param_name)
        
        return {
            'name': self.name,
            'description': self.description,
            'input_schema': {
                'type': 'object',
                'properties': properties,
                'required': required
            }
        }
    
    @abstractmethod
    def execute(self, repository, **params) -> Dict[str, Any]:
        pass
