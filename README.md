# DataGrapho BackEnd

API Django do DataGrapho, incluindo autenticacao, administracao, De/Para e o
assistente de dados com function calling.

## Configurar o chatbot localmente

1. Crie o ambiente virtual e instale as dependencias:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

2. Copie `.env.example` para `.env` e configure um provider compativel
   (Gemini, OpenAI ou uma API local do LM Studio). O arquivo `.env` e ignorado
   pelo Git e nao deve ser versionado.

3. Prepare o banco e inicie a API:

   ```powershell
   python manage.py migrate
   python manage.py runserver
   ```

4. Autentique-se e consulte `GET /api/chatbot/health/`. O retorno deve indicar
   `status: ok`, `ai_configured: true` e listar `get_wine_by_name` entre as
   ferramentas.

5. Envie uma pergunta autenticada:

   ```http
   POST /api/chatbot/chat/
   Authorization: Bearer <access-token>
   Content-Type: application/json

   {"message": "Qual e o pais e o preco do vinho Alma Negra?"}
   ```

O modelo nao acessa o banco diretamente. Ele escolhe uma ferramenta registrada,
o backend executa uma consulta Django ORM controlada e devolve o resultado ao
modelo para redacao da resposta.

## Dados de vinho

O banco preserva `FatoConsumoVinho` para o historico de consumo e possui um
catalogo relacional separado: paises, regioes, produtores, uvas, vinhos,
composicoes, ofertas/safras e avaliacoes. A ferramenta `get_wine_by_name`
consulta primeiro esse catalogo e usa a tabela historica como fallback.

`search_wine_catalog` permite combinar filtros de pais, regiao, produtor, uva,
cor, tipo, preco, estoque e avaliacao. `get_wine_database_summary` agrupa os
vinhos por uma dessas dimensoes e aceita `catalogo`, `historico` ou `todos` como
fonte. Em `todos`, nomes repetidos sao deduplicados e eventuais empates sao
informados. As migrations incluem oito vinhos marcados como demonstrativos,
com precos e notas ficticios, para testes locais.

## Testes

```powershell
pytest -q
```

Os testes do motor usam um provider falso: validam o ciclo de function calling
sem consumir cota nem depender de uma chave externa.
