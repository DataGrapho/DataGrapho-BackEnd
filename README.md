# DataGrapho-BackEnd
Repo dedicado a criação do projeto de BACKEND DATAGRAPHO

## 🐳 Ambiente com Docker

O projeto está configurado para rodar utilizando Docker e Docker Compose, garantindo um ambiente padronizado para desenvolvimento.

### Serviços

- **Backend (Django)**: aplicação principal
- **PostgreSQL**: banco de dados

### Inicialização

O container do backend utiliza um `entrypoint.sh` responsável por:

- Aguardar o banco de dados ficar disponível
- Executar as migrations automaticamente
- Iniciar o servidor Django

### Como executar

```bash
docker compose up --build