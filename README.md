# EAS - API RAG Base de Conhecimento

API Python para Base de Conhecimento RAG (Retrieval Augmented Generation) para projetos de IA.

## Visão Geral

Esta API permite criar uma base de conhecimento inteligente com:

- **Scraping Inteligente**: Coleta automática de dados de sites de fitness/hipertrofia e bases científicas
- **Busca Semântica**: Pesquisa usando embeddings vetoriais (pgvector)
- **IA Orquestradora**: OpenRouter (GPT-4o/Claude) para extração inteligente
- **API Keys**: Autenticação com hash MD5

## Início Rápido

```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Configurar variáveis de ambiente
cp .env.example .env
# Edite .env com suas credenciais

# 3. Configurar banco de dados
# Execute database/schema.sql no Supabase

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

## Tecnologias

- FastAPI + Uvicorn
- Supabase (PostgreSQL + pgvector)
- OpenRouter (GPT-4o, Claude 3.5)
- BeautifulSoup4 + httpx
- APScheduler

## Endpoints Principais

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `GET` | `/api/v1/health` | Health check |
| `POST` | `/api/v1/search` | Busca semântica |
| `POST` | `/api/v1/knowledge` | Criar conhecimento |
| `POST` | `/api/v1/api-keys` | Criar API Key |
| `GET` | `/api/v1/scraper/status` | Status do scraper |

## Docker

```bash
docker-compose up -d
```

## Licença

MIT