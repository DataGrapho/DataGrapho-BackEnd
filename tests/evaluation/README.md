# Avaliação do chatbot com modelo real

Execute no diretório do backend, com o servidor do modelo local ativo:

```powershell
.venv\Scripts\python.exe tests\evaluation\evaluate_chatbot.py
```

O padrão usa `qwen2.5-7b-instruct` em `http://127.0.0.1:1234/v1`. Para outro modelo ou endpoint OpenAI-compatible:

```powershell
.venv\Scripts\python.exe tests\evaluation\evaluate_chatbot.py --model nome-do-modelo --base-url http://127.0.0.1:1234/v1
```

Para um provedor que exige chave, informe somente o nome de uma variável de ambiente que já contenha a chave: `--api-key-env AI_API_KEY`. A chave não é impressa. `--case specific_wine` executa apenas um cenário.

O comando cria um banco SQLite temporário em memória com quatro vinhos conhecidos (um deles sem estoque) e executa seis perguntas. Ele usa o fluxo real de ferramentas e de geração de resposta. A saída JSON informa, por cenário:

- se a IA selecionou uma ferramenta adequada;
- se passou os filtros esperados sem acrescentar restrições que mudem o resultado;
- se nomes, países e preços citados têm suporte nos dados retornados;
- a resposta livre da IA, as chamadas de ferramentas e os tokens informados pelo provedor.

Os casos descrevem fatos e comportamento esperados **somente para avaliação**. Eles não são carregados pelo chatbot durante o atendimento e não determinam o texto da resposta. O verificador cobre fatos estruturados selecionados; afirmações em linguagem natural que não envolvem esses campos ainda precisam de revisão humana. Cada execução é uma amostra, pois a resposta do modelo pode variar.

Relatórios de execuções locais podem ficar em `benchmarks/`, que é ignorado pelo Git.
