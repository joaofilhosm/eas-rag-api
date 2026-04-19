# EAS - API RAG Base de Conhecimento

API Python para Base de Conhecimento RAG (Retrieval Augmented Generation) para projetos de IA.

## Visão Geral

Esta API permite:

- **Scraping Inteligente**: Coleta automática de dados de sites de fitness/hipertrofia e bases científicas
- **Busca Semântica**: Pesquisa inteligente usando embeddings vetoriais (pgvector)
- **Base de Conhecimento**: Armazenamento estruturado de conhecimento para RAG
- **API Keys**: Gerenciamento de chaves de acesso com hash MD5
- **IA Orquestradora**: OpenRouter (GPT-4o/Claude) para extração inteligente de conteúdo

## Fontes de Dados

### Fitness/Hipertrofia
- **Dicas de Treino**: https://www.dicasdetreino.com.br
- **Hipertrofia.org**: https://www.hipertrofia.org

### Científicas
- **SciELO**: Artigos científicos em português/espanhol/inglês
- **PubMed**: Artigos biomédicos
- **LILACS**: Literatura latino-americana
- **CAPES**: Portal de periódicos acadêmicos

## Arquitetura

```
┌─────────────────────────────────────────────────────────────────┐
│                        API EAS                                   │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐   ┌─────────────┐   ┌──────────────────────┐   │
│  │   FastAPI   │──▶│   RAG       │──▶│   Supabase          │   │
│  │   :8000     │   │   Search    │   │   + pgvector        │   │
│  └─────────────┘   └─────────────┘   └──────────────────────┘   │
│         │                                     ▲                  │
│         │              ┌──────────────────────┘                  │
│         ▼              │                                         │
│  ┌─────────────┐   ┌─────────────┐   ┌──────────────────────┐   │
│  │   Auth      │   │   Scraper   │──▶│   OpenRouter        │   │
│  │   MD5 Key   │   │   Scheduler │   │   GPT-4o/Claude      │   │
│  └─────────────┘   └─────────────┘   └──────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Tecnologias

- **FastAPI**: Framework web assíncrono
- **Supabase**: Banco de dados PostgreSQL + pgvector
- **OpenRouter**: Provider de LLM (GPT-4o, Claude 3.5)
- **BeautifulSoup4**: Parsing de HTML
- **APScheduler**: Agendamento de tarefas
- **httpx**: Cliente HTTP assíncrono

## Início Rápido

### 1. Pré-requisitos

- Python 3.11+
- Conta no Supabase (gratuita)
- Conta no OpenRouter (ou OpenAI)
- Docker (opcional)

### 2. Configuração

```bash
# Clone o repositório
cd eas

# Crie ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
.\venv\Scripts\activate  # Windows

# Instale dependências
pip install -r requirements.txt

# Configure variáveis de ambiente
cp .env.example .env
# Edite .env com suas credenciais
```

### 3. Configurar Supabase

1. Crie um projeto no [Supabase](https://supabase.com)
2. Execute o SQL em `database/schema.sql` no SQL Editor
3. Copie as credenciais para `.env`

### 4. Executar

```bash
# Desenvolvimento
python run.py

# Ou com uvicorn direto
uvicorn app.main:app --reload
```

### 5. Acessar

- API: http://localhost:8000
- Docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Endpoints Principais

### Health Check
```
GET /api/v1/health
GET /api/v1/health/detailed
GET /api/v1/stats
```

### API Keys
```
POST /api/v1/api-keys          # Criar nova API Key
GET  /api/v1/api-keys          # Listar keys
GET  /api/v1/api-keys/{id}     # Buscar key
DELETE /api/v1/api-keys/{id}   # Desativar key
```

### Busca RAG
```
POST /api/v1/search            # Busca semântica
POST /api/v1/search/similar/{id} # Encontrar similares
GET  /api/v1/search/suggestions  # Sugestões de busca
```

### Knowledge Base
```
POST   /api/v1/knowledge       # Criar conhecimento
GET    /api/v1/knowledge       # Listar
GET    /api/v1/knowledge/{id}  # Buscar por ID
PUT    /api/v1/knowledge/{id}  # Atualizar
DELETE /api/v1/knowledge/{id}  # Deletar
```

### Scraper
```
GET  /api/v1/scraper/status    # Status do scraper
POST /api/v1/scraper/start     # Iniciar scraping
POST /api/v1/scraper/stop      # Parar scraping
GET  /api/v1/sources           # Listar fontes
POST /api/v1/sources           # Adicionar fonte
```

## Autenticação

Todas as requisições (exceto health check) requerem API Key:

```bash
curl -H "X-API-Key: eas_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" http://localhost:8000/api/v1/search
```

Para criar API Keys, use a Master Key:

```bash
curl -X POST \
  -H "X-Master-Key: sua-master-key" \
  -H "Content-Type: application/json" \
  -d '{"name": "Minha App", "description": "App de teste"}' \
  http://localhost:8000/api/v1/api-keys
```

## Docker

```bash
# Build
docker build -t eas-api .

# Run
docker run -p 8000:8000 --env-file .env eas-api

# Ou com docker-compose
docker-compose up -d
```

## Variáveis de Ambiente

| Variável | Descrição | Obrigatório |
|----------|-----------|-------------|
| `SUPABASE_URL` | URL do projeto Supabase | ✅ |
| `SUPABASE_KEY` | Chave anon do Supabase | ✅ |
| `SUPABASE_SERVICE_KEY` | Chave service role | ✅ |
| `OPENROUTER_API_KEY` | API Key do OpenRouter | ✅ |
| `API_MASTER_KEY` | Master key para gerenciar API Keys | ✅ |
| `DEFAULT_MODEL` | Modelo LLM padrão | ❌ |
| `SCRAPER_DELAY_SECONDS` | Delay entre requisições | ❌ |

## Estrutura do Projeto

```
eas/
├── app/
│   ├── main.py              # FastAPI app
│   ├── config.py            # Configurações
│   ├── models/              # Modelos Pydantic
│   ├── routers/             # Endpoints
│   ├── services/            # Lógica de negócio
│   └── utils/               # Utilitários
├── scraper/
│   ├── base_scraper.py      # Classe base
│   ├── sources/             # Scrapers específicos
│   ├── ai_orchestrator.py   # IA para extração
│   └── scheduler.py         # Agendamento
├── database/
│   ├── schema.sql           # Schema PostgreSQL
│   └── supabase_client.py   # Cliente Supabase
├── docs/
│   ├── README.md            # Este arquivo
│   ├── API.md               # Documentação da API
│   ├── SETUP.md             # Guia de instalação
│   └── lovable_prompt.md    # Prompt para Lovable
├── tests/                   # Testes
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── run.py                   # Entry point
```

## Licença

MIT License

## Contribuição

1. Fork o projeto
2. Crie uma branch (`git checkout -b feature/nova-funcionalidade`)
3. Commit suas mudanças (`git commit -m 'Adiciona nova funcionalidade'`)
4. Push para a branch (`git push origin feature/nova-funcionalidade`)
5. Abra um Pull Request

## Contato

Para dúvidas ou sugestões, abra uma issue no repositório.