Chatbot inteligente que usa **Google Gemini** para responder perguntas sobre dados financeiros. A IA **não inventa respostas** - ela busca informações reais do banco de dados através de **ferramentas (tools)** usando **Function Calling**.

**Como funciona:**
- Usuário faz pergunta em linguagem natural
- IA decide quais ferramentas usar
- Backend executa ferramentas e busca dados no PostgreSQL
- IA recebe resultados e formata resposta
- Suporta **múltiplas chamadas** (até 5) para perguntas complexas

**Exemplos:**
- "Quais são os 10 principais clientes?"
- "Qual foi a receita em janeiro de 2025?"
- "Compare a receita de janeiro com fevereiro"

**Tempo médio:** 3-5 segundos por resposta


---

## 🔄 Como Funciona

```
Usuário pergunta
    ↓
IA decide qual(is) tool(s) usar
    ↓
Backend executa tool(s) → PostgreSQL
    ↓
IA recebe dados e formata resposta
    ↓
Usuário vê resposta formatada
```

---

## 🏗️ Arquitetura

### Visão em Camadas

```
┌─────────────────────────────────────────────┐
│  API Layer (Django REST)                    │
│  • Endpoint: POST /api/chatbot/chat/        │
│  • Validação JWT                            │
│  • Rate limiting (10 req/min)               │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  Service Layer                              │
│  • Gerenciamento de sessões                │
│  • Histórico de conversas                  │
│  • Orquestração                            │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  Core Engine (Function Calling)             │
│  • Loop multi-turn (até 5 iterações)       │
│  • Comunicação com IA                      │
│  • Execução de tools                       │
└─────────────────────────────────────────────┘
            ↓                    ↓
┌──────────────────────┐  ┌──────────────────┐
│  AI Provider         │  │  Tool Registry   │
│  • Gemini API        │  │  • 4 tools       │
│  • Function Calling  │  │  • Validação     │
└──────────────────────┘  └──────────────────┘
                                  ↓
                    ┌──────────────────────────┐
                    │  Repository + Database   │
                    │  • PostgreSQL            │
                    │  • Django ORM            │
                    │  • Cache (5 min)         │
                    └──────────────────────────┘
```

---

## 🔧 Function Calling: O que é?

**Function Calling** é um protocolo nativo das APIs de IA (OpenAI, Gemini, Anthropic) que permite a IA **solicitar execução de funções** em vez de apenas gerar texto.

**Como funciona:**
- ✅ Backend envia **definições** das ferramentas (schema) para a IA
- ✅ IA **analisa** a pergunta e **decide** quais ferramentas chamar
- ✅ Backend **executa** as ferramentas localmente e busca dados
- ✅ IA **recebe resultados** e formata resposta em linguagem natural

**O que NÃO é:**
- ❌ IA **não executa** código nem acessa banco diretamente
- ❌ **Não é** GraphQL, REST ou RPC tradicional
- ❌ **Não é** prompt engineering com parsing de texto

---

### Fluxo Simplificado

```
1. Usuário faz pergunta
        ↓
2. Backend envia para IA:
   - Pergunta do usuário
   - Definições das 4 ferramentas (schema)
   - Histórico da conversa
        ↓
3. IA analisa e decide:
   - Preciso chamar ferramenta? → Sim
   - Qual ferramenta? → get_top_customers
   - Quais parâmetros? → {"limit": 10}
        ↓
4. Backend executa ferramenta:
   - Valida parâmetros
   - Executa query no PostgreSQL
   - Retorna dados: [{"name": "Tech 5", "revenue": 245320.50}, ...]
        ↓
5. Backend envia resultado para IA
        ↓
6. IA processa dados e gera resposta formatada:
   "Os 10 principais clientes por receita total são:
    1. Tecnologia 5 Ltda - R$ 245.320,50
    2. Varejo 12 S.A. - R$ 198.450,00
    ..."
        ↓
7. Usuário recebe resposta
```

**Importante:** 
- Passos 3-5 podem se repetir até 5 vezes (multi-turn)
- IA decide autonomamente quando tem dados suficientes para responder

---

## ⚙️ Detalhes Técnicos Importantes

### 1. Conversão de Formato (Format Conversion)

As ferramentas são definidas internamente em **formato OpenAI** (padrão) e convertidas para o formato específico de cada provider.

**Formato Interno (OpenAI):**
```json
{
  "type": "function",
  "function": {
    "name": "get_top_customers",
    "description": "Obter os principais clientes por receita total",
    "parameters": {
      "type": "object",
      "properties": {
        "limit": {
          "type": "integer",
          "description": "Número de clientes (1-100)"
        }
      },
      "required": ["limit"]
    }
  }
}
```

**Conversão para Gemini:**
```python
# gemini_provider.py - format_tool_definitions()
function_declaration = genai.protos.FunctionDeclaration(
    name="get_top_customers",
    description="Obter os principais clientes...",
    parameters=genai.protos.Schema(
        type=genai.protos.Type.OBJECT,
        properties={
            "limit": genai.protos.Schema(
                type=genai.protos.Type.INTEGER,
                description="Número de clientes (1-100)"
            )
        },
        required=["limit"]
    )
)
```

**Vantagem:** Trocar de provider (OpenAI → Gemini → Anthropic) requer apenas mudar 3 linhas no `.env`

---

### 2. Retry com Exponential Backoff

Todas as chamadas à API da IA incluem **retry automático** com backoff exponencial.

**Implementação:**
```python
# base.py - _exponential_backoff()
def _exponential_backoff(self, attempt: int) -> float:
    """Calculate exponential backoff delay."""
    return min(2 ** attempt, 30)  # Max 30 segundos

# Tentativas:
# Attempt 0: 1 segundo
# Attempt 1: 2 segundos
# Attempt 2: 4 segundos
# Attempt 3: 8 segundos
```

**Erros tratados:**
- Rate limit (429)
- Timeout
- Erros temporários de rede

**Configuração:**
- `max_retries`: 3 tentativas
- `timeout`: 120 segundos por chamada

---

### 3. Gerenciamento de Histórico de Conversas

O histórico completo é enviado em **cada chamada** para manter contexto.

**Estrutura:**
```python
messages = [
    AIMessage(role='user', content='Qual foi a receita em janeiro?'),
    AIMessage(role='assistant', tool_calls=[...]),
    AIMessage(role='tool', content='{"total": 125430.50}', name='get_revenue_by_period'),
    AIMessage(role='assistant', content='A receita foi R$ 125.430,50'),
    AIMessage(role='user', content='E em fevereiro?'),  # Nova pergunta
]
```

**Importante para Gemini:**
- Gemini requer histórico completo via `start_chat(history=...)`
- Bug crítico corrigido: enviar histórico vazio causava erro "function response must come after function call"
- Solução: enviar todas as mensagens anteriores como histórico antes da nova mensagem

---

### 4. Validação de Parâmetros

Cada ferramenta valida seus parâmetros antes de executar.

**Exemplo:**
```python
# financial/tools.py - GetTopCustomersTool
def execute(self, repository, limit: int = 10):
    # Validação
    if not isinstance(limit, int):
        raise ValueError("limit must be an integer")
    if limit < 1 or limit > 100:
        raise ValueError("limit must be between 1 and 100")
    
    # Execução
    return repository.get_top_customers(limit)
```

**Camadas de validação:**
1. IA valida contra schema antes de chamar
2. Backend valida JSON parsing
3. Tool valida tipos e ranges
4. Repository valida queries SQL

---

### 5. System Prompt Otimizado

O system prompt instrui a IA sobre formatação e comportamento.

**Conteúdo:**
```python
system_instruction = (
    "Você é um assistente financeiro inteligente. "
    "Ao apresentar valores monetários, sempre use o símbolo R$ "
    "e separadores de milhares (ex: R$ 150.000,00). "
    "Ao apresentar datas, use formato legível em português "
    "(ex: 'janeiro de 2024', '15 de março'). "
    "Seja claro, objetivo e profissional nas respostas. "
    "Se precisar de múltiplas ferramentas para responder, use-as em sequência."
)
```

**Resultado:** Respostas consistentes e bem formatadas

---

### 6. Tratamento de Erros em Camadas

Erros são tratados em cada camada com mensagens apropriadas.

**Camadas:**

```
API Layer (controller.py)
    ↓ Captura: ValidationError, AuthenticationError
    ↓ Retorna: HTTP 400, 401, 500

Service Layer (service.py)
    ↓ Captura: Erros do Engine
    ↓ Retorna: Mensagem amigável

Engine Layer (engine.py)
    ↓ Captura: Erros de AI Provider, Tool execution
    ↓ Retorna: ExecutionResult com error field

AI Provider (gemini_provider.py)
    ↓ Captura: Rate limit, Timeout, API errors
    ↓ Retry com backoff

Tool Layer (tools.py)
    ↓ Captura: Validation errors
    ↓ Retorna: ValueError com mensagem clara

Repository Layer (repository.py)
    ↓ Captura: Database errors
    ↓ Retorna: QueryError
```

**Exemplo de erro tratado:**
```
Usuário: "Quais são os 1000 principais clientes?"
Tool valida: limit > 100
Retorna: "limit must be between 1 and 100"
IA reformula: "Desculpe, posso mostrar no máximo 100 clientes. 
               Gostaria de ver os top 100?"
```

---

### 7. Auditoria e Logging

Todas as operações são logadas para auditoria e debugging.

**Logs importantes:**
```python
# Início de execução
logger.info(f"Starting query execution: user_message='{message[:50]}...'")

# Chamada de tool
logger.info(f"AUDIT: tool_execution, tool={tool_name}, iteration={iteration}")

# Performance
logger.info(f"⏱️ AI Provider call took {duration:.2f}s")
logger.info(f"⏱️ Tool {tool_name} executed in {duration:.2f}s")

# Resultado
logger.info(f"✅ AI provided final response. Total time: {total_time:.2f}s")
```

**Informações rastreadas:**
- Tempo de cada chamada (IA, tool, total)
- Ferramentas executadas
- Número de iterações
- Erros e retries

---

## 🔄 Processamento Multi-Turn (Rechamadas)

Uma das funcionalidades mais importantes é o **processamento de múltiplas chamadas** para responder perguntas complexas.

### Como Funciona

A IA pode chamar **várias ferramentas em sequência** (até 5 iterações) para coletar todas as informações necessárias antes de responder.

**Exemplo: Pergunta Complexa**

```
Pergunta: "Qual foi o lucro líquido em janeiro e quem foram os top 3 clientes?"
```

**Execução:**

```
┌─────────────────────────────────────────────────────────┐
│ Iteração 1: IA chama get_revenue_by_period             │
├─────────────────────────────────────────────────────────┤
│ Tool: get_revenue_by_period("2025-01-01", "2025-01-31")│
│ Backend executa → PostgreSQL                            │
│ Resultado: {"total": 125430.50}                        │
│ Backend envia resultado de volta para IA               │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ Iteração 2: IA chama get_expenses_by_category          │
├─────────────────────────────────────────────────────────┤
│ Tool: get_expenses_by_category("2025-01")              │
│ Backend executa → PostgreSQL                            │
│ Resultado: {"total": 87250.30}                         │
│ Backend envia resultado de volta para IA               │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ Iteração 3: IA chama get_top_customers                 │
├─────────────────────────────────────────────────────────┤
│ Tool: get_top_customers(3)                              │
│ Backend executa → PostgreSQL                            │
│ Resultado: [Tech 5, Varejo 12, Serviços 8]            │
│ Backend envia resultado de volta para IA               │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ Iteração 4: IA processa todos os dados e responde      │
├─────────────────────────────────────────────────────────┤
│ "Em janeiro de 2025:                                    │
│  • Receita: R$ 125.430,50                              │
│  • Despesas: R$ 87.250,30                              │
│  • Lucro Líquido: R$ 38.180,20                         │
│                                                         │
│  Top 3 clientes:                                        │
│  1. Tecnologia 5 Ltda - R$ 45.320,50                  │
│  2. Varejo 12 S.A. - R$ 38.450,00                     │
│  3. Serviços 8 EIRELI - R$ 27.900,25"                 │
└─────────────────────────────────────────────────────────┘
```

### Controle de Iterações

- **Máximo:** 5 iterações por pergunta
- **Motivo:** Evitar loops infinitos e controlar custos
- **Implementação:** Loop no `FunctionCallingEngine` (`core/engine.py`)

```python
# Pseudocódigo do loop
iteration = 0
while iteration < MAX_TOOL_CALLS:
    response = ai_provider.chat_completion(messages, tools)
    
    if response.has_tool_calls:
        # Executar ferramentas
        for tool_call in response.tool_calls:
            result = execute_tool(tool_call)
            messages.append(tool_result)
        iteration += 1
    else:
        # IA retornou resposta final
        return response.content
```

---

## � Exemplos de Usoe

### Exemplo 1: Pergunta Simples (1 tool)
```
Pergunta: "Qual foi a receita em janeiro de 2025?"

Execução:
  Iteração 1: get_revenue_by_period("2025-01-01", "2025-01-31")
              → {"total": 125430.50, "count": 15}
  
  Iteração 2: IA formata resposta
              → "A receita total em janeiro de 2025 foi de 
                 R$ 125.430,50, distribuída em 15 transações."

Tempo: ~3.5 segundos
```

### Exemplo 2: Pergunta Multi-Tool (3 tools)
```
Pergunta: "Mostre receita, despesas e top 5 clientes de janeiro"

Execução:
  Iteração 1: get_revenue_by_period(...) → R$ 125.430,50
  Iteração 2: get_expenses_by_category(...) → R$ 87.250,30
  Iteração 3: get_top_customers(5) → [Tech 5, Varejo 12, ...]
  Iteração 4: IA formata resposta completa

Tempo: ~8.5 segundos
```

---

## 📊 Performance

| Métrica | Valor |
|---------|-------|
| Tempo médio de resposta | 3-5 segundos |
| Tempo de chamada IA | 2-4 segundos |
| Tempo de execução tool | 0.1-0.5 segundos |
| Máximo de iterações | 5 por pergunta |
| Timeout por chamada | 120 segundos |
| Retries automáticos | 3 tentativas |

**Otimizações:**
- Cache de queries (5 min)
- Retry com exponential backoff
- Queries otimizadas com aggregations
- Logs de performance (⏱️)

---

## ✨ Diferenciais

✅ **Dados reais** - não inventa informações  
✅ **Inteligência autônoma** - IA decide quais tools usar  
✅ **Multi-turn** - combina múltiplas ferramentas automaticamente  
✅ **Multi-provider** - troca OpenAI/Gemini/Anthropic mudando `.env`  
✅ **Extensível** - fácil adicionar novas tools e domínios  
✅ **Resiliente** - retry automático com backoff exponencial  
✅ **Auditável** - logs detalhados de execução  
✅ **Seguro** - JWT, rate limiting, validação em camadas  

---

## 🎓 Glossário

**Function Calling:** Protocolo nativo de APIs de IA para solicitar execução de funções

**Tool:** Função que a IA pode chamar para buscar dados (tem nome, descrição e schema)

**Multi-Turn:** Execução em múltiplas iterações, permitindo uso sequencial de várias tools

**Provider:** Serviço de IA (OpenAI, Gemini, Anthropic)

**Exponential Backoff:** Estratégia de retry que aumenta tempo entre tentativas (1s, 2s, 4s, 8s...)

**Schema:** Definição estruturada dos parâmetros de uma tool (tipos, descrições, obrigatoriedade)

---

**Versão:** 2.0 | **Status:** ✅ Em produção
