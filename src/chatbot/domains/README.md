# Chatbot Domains - Arquitetura Modular

Esta pasta contém domínios plugáveis para o chatbot. Cada domínio é independente e pode ser ativado/desativado via configuração.

## Domínios Disponíveis

### ✅ Financial (Financeiro)
- **Status**: Implementado
- **Models**: Customer, Revenue, Expense
- **Tools**: get_revenue_by_period, get_expenses_by_category, get_top_customers, compare_periods
- **Descrição**: Análise de dados financeiros (receitas, despesas, clientes)

### 🚧 HR (Recursos Humanos)
- **Status**: Não implementado
- **Models sugeridos**: Employee, Payroll, Benefits, Department
- **Tools sugeridas**: get_employees_by_department, get_payroll_summary, get_benefits_by_employee
- **Descrição**: Gestão de RH (funcionários, folha de pagamento, benefícios)

### 🚧 Sales (Vendas)
- **Status**: Não implementado
- **Models sugeridos**: Lead, Opportunity, Deal, SalesRep
- **Tools sugeridas**: get_pipeline_status, get_deals_by_stage, get_sales_rep_performance
- **Descrição**: Gestão de vendas (leads, oportunidades, pipeline)

## Como Adicionar um Novo Domínio

### 1. Criar Estrutura de Pastas

```bash
chatbot/domains/
└── seu_dominio/
    ├── __init__.py
    ├── models.py          # Django models
    ├── tools.py           # Tools para o chatbot
    ├── repository.py      # Queries de banco de dados
    └── seed_data.py       # Dados de exemplo (opcional)
```

### 2. Implementar Models (models.py)

```python
"""Models do domínio seu_dominio."""

from django.db import models

class SeuModel(models.Model):
    """Descrição do model."""
    
    # Campos do model
    name = models.CharField(max_length=200)
    
    class Meta:
        db_table = 'chatbot_seu_model'
        verbose_name = 'Seu Model'
```

### 3. Implementar Tools (tools.py)

```python
"""Tools do domínio seu_dominio."""

from chatbot.core.base_tool import Tool

class SuaTool(Tool):
    """Descrição da tool."""
    
    def __init__(self):
        super().__init__(
            name='sua_tool',
            description='Descrição do que a tool faz',
            parameters={
                'param1': 'string',
                'param2': 'integer'
            }
        )
    
    def execute(self, repository, **params):
        """Executa a tool."""
        return repository.sua_query(params['param1'], params['param2'])


def register_seu_dominio_tools(registry):
    """Registra todas as tools do domínio."""
    registry.register_tool(SuaTool())
    # Adicione mais tools aqui
```

### 4. Implementar Repository (repository.py)

```python
"""Repository do domínio seu_dominio."""

from chatbot.domains.seu_dominio.models import SeuModel

class Seu_dominioRepository:
    """Repository para queries do domínio."""
    
    def sua_query(self, param1, param2):
        """Executa query no banco."""
        results = SeuModel.objects.filter(name=param1)
        return {
            'results': list(results.values()),
            'count': results.count()
        }
```

### 5. Criar Migration

```bash
python manage.py makemigrations
python manage.py migrate
```

### 6. Ativar o Domínio

**Opção 1: Via settings.py**
```python
CHATBOT_CONFIG = {
    'ACTIVE_DOMAINS': ['financial', 'seu_dominio'],
    # ...
}
```

**Opção 2: Via variável de ambiente**
```bash
export CHATBOT_ACTIVE_DOMAINS=financial,seu_dominio
```

### 7. Testar

```python
# O chatbot agora tem acesso às tools do seu domínio!
# Pergunte algo relacionado ao domínio e a IA vai usar as tools
```

## Múltiplos Domínios Simultâneos

Você pode ativar múltiplos domínios ao mesmo tempo:

```python
CHATBOT_CONFIG = {
    'ACTIVE_DOMAINS': ['financial', 'hr', 'sales'],
}
```

O chatbot terá acesso a **todas as tools** de todos os domínios ativos e poderá responder perguntas sobre qualquer um deles!

## Exemplo: Adicionando Domínio HR

### 1. Criar pasta e arquivos

```bash
mkdir -p chatbot/domains/hr
touch chatbot/domains/hr/__init__.py
touch chatbot/domains/hr/models.py
touch chatbot/domains/hr/tools.py
touch chatbot/domains/hr/repository.py
```

### 2. models.py

```python
from django.db import models

class Employee(models.Model):
    name = models.CharField(max_length=200)
    department = models.CharField(max_length=100)
    salary = models.DecimalField(max_digits=10, decimal_places=2)
    hire_date = models.DateField()
    
    class Meta:
        db_table = 'chatbot_employee'
```

### 3. tools.py

```python
from chatbot.core.base_tool import Tool

class GetEmployeesByDepartmentTool(Tool):
    def __init__(self):
        super().__init__(
            name='get_employees_by_department',
            description='Obter funcionários por departamento',
            parameters={'department': 'string'}
        )
    
    def execute(self, repository, **params):
        return repository.get_employees_by_department(params['department'])

def register_hr_tools(registry):
    registry.register_tool(GetEmployeesByDepartmentTool())
```

### 4. repository.py

```python
from chatbot.domains.hr.models import Employee

class HrRepository:
    def get_employees_by_department(self, department):
        employees = Employee.objects.filter(department=department)
        return {
            'employees': list(employees.values()),
            'count': employees.count()
        }
```

### 5. Ativar

```python
CHATBOT_CONFIG = {
    'ACTIVE_DOMAINS': ['financial', 'hr'],
}
```

Pronto! Agora o chatbot pode responder perguntas sobre finanças E RH! 🎉

## Vantagens da Arquitetura Modular

✅ **Fácil expansão**: Adicione novos domínios sem tocar no core
✅ **Isolamento**: Cada domínio é independente
✅ **Múltiplos contextos**: Chatbot pode atuar em vários domínios simultaneamente
✅ **Manutenibilidade**: Código organizado por domínio
✅ **Reutilização**: Core (engine, AI providers) é compartilhado

## Estrutura Completa

```
chatbot/
├── core/                      # Núcleo (não muda)
│   ├── base_tool.py          # Classe base Tool
│   ├── tool_registry.py      # Registro de tools
│   ├── domain_loader.py      # Carregador de domínios
│   └── ai_providers/         # OpenAI/Anthropic
│
├── domains/                   # Domínios plugáveis
│   ├── financial/            # Domínio financeiro
│   │   ├── models.py
│   │   ├── tools.py
│   │   └── repository.py
│   │
│   ├── hr/                   # Domínio RH
│   │   ├── models.py
│   │   ├── tools.py
│   │   └── repository.py
│   │
│   └── README.md             # Este arquivo
│
├── models.py                  # Core models (ChatSession, ChatMessage)
├── controller.py              # API endpoint
├── service.py                 # Business logic
└── router.py                  # URL routing
```
