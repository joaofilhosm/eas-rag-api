# EAS - API RAG Base de Conhecimento

API Python para Base de Conhecimento RAG (Retrieval Augmented Generation) para projetos de IA.

## Visão Geral

Esta API permite criar uma base de conhecimento inteligente com:

- **Scraping Inteligente**: Coleta automática de dados de sites de fitness/hipertrofia e bases científicas
- **Busca Semântica**: Pesquisa usando embeddings vetoriais (pgvector)
- **IA Orquestradora**: OpenRouter (GPT-4o/Claude) para extração inteligente
- **API Keys**: Autenticação com hash MD5
- **PostgreSQL + pgvector**: Banco de dados self-hosted

## Stack Tecnológica

- **FastAPI** - Framework web assíncrono
- **PostgreSQL + pgvector** - Banco de dados com busca vetorial
- **OpenRouter** - Provider de LLM (GPT-4o, Claude 3.5)
- **asyncpg** - Cliente PostgreSQL assíncrono
- **Docker** - Containerização

## Início Rápido

### Com Docker (Recomendado)

```bash
# Clonar e iniciar
git clone https://github.com/joaofilhosm/eas-rag-api.git
cd eas-rag-api

# Configurar variáveis de ambiente
cp .env.example .env
# Edite .env com suas credenciais

# Iniciar serviços
docker-compose up -d

# Acessar API
curl http://localhost:8000/api/v1/health
```

### Instalação Local

```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Configurar PostgreSQL com pgvector
createdb eas_rag
psql -d eas_rag -f database/schema.sql

# 3. Configurar variáveis de ambiente
cp .env.example .env
# Edite .env

# 4. Executar
python run.py
```

## Documentação

- [README Completo](docs/README.md)
- [Documentação da API](docs/API.md)
- [Guia de Instalação](docs/SETUP.md)
- [Prompt para Lovable](docs/lovable_prompt.md)

## Fontes de Dados

### Fitness/Hipertrofia
- Dicas de Treino (dicasdetreino.com.br)
- Hipertrofia.org

### Científicas
- SciELO
- PubMed
- LILACS
- CAPES

## Endpoints Principais

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `GET` | `/api/v1/health` | Health check |
| `POST` | `/api/v1/search` | Busca semântica |
| `POST` | `/api/v1/knowledge` | Criar conhecimento |
| `POST` | `/api/v1/api-keys` | Criar API Key |
| `GET` | `/api/v1/scraper/status` | Status do scraper |

## Docker Compose

```yaml
services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: eas_rag
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  eas-api:
    build: .
    ports:
      - "8000:8000"
    env_file: .env
    depends_on:
      - postgres
```

## Variáveis de Ambiente

| Variável | Descrição | Obrigatório |
|----------|-----------|-------------|
| `DATABASE_URL` | URL de conexão PostgreSQL | ✅ |
| `OPENROUTER_API_KEY` | API Key OpenRouter | ✅ |
| `API_MASTER_KEY` | Master key para admin | ✅ |

## Licença

MIT

## Autor

joaofilhosm