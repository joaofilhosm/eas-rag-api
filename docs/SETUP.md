# Guia de Instalação - EAS API RAG

## Índice

1. [Pré-requisitos](#pré-requisitos)
2. [Configuração do PostgreSQL](#configuração-do-postgresql)
3. [Configuração do OpenRouter](#configuração-do-openrouter)
4. [Instalação Local](#instalação-local)
5. [Instalação com Docker](#instalação-com-docker)
6. [Variáveis de Ambiente](#variáveis-de-ambiente)
7. [Testando a Instalação](#testando-a-instalação)
8. [Troubleshooting](#troubleshooting)

---

## Pré-requisitos

### Obrigatórios

- **Python 3.11+** (recomendado 3.12)
- **PostgreSQL 16+** com extensão **pgvector**
- **Conta no OpenRouter** (ou OpenAI) - [openrouter.ai](https://openrouter.ai)

### Opcionais

- **Docker** e **Docker Compose** (para containerização)
- **Git** (para versionamento)

---

## Configuração do PostgreSQL

### Opção 1: Docker (Recomendado)

```bash
# Usar a imagem oficial com pgvector
docker run -d \
  --name eas-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=eas_rag \
  -p 5432:5432 \
  pgvector/pgvector:pg16
```

### Opção 2: Instalação Local

#### Ubuntu/Debian

```bash
# Adicionar repositório do PostgreSQL
sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
wget -qO- https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo tee /etc/apt/trusted.gpg.d/pgdg.asc &>/dev/null

# Instalar PostgreSQL 16
sudo apt update
sudo apt install postgresql-16 postgresql-16-pgvector

# Iniciar serviço
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Criar banco de dados
sudo -u postgres psql -c "CREATE DATABASE eas_rag;"
sudo -u postgres psql -c "CREATE EXTENSION IF NOT EXISTS vector;" eas_rag
```

#### Windows

1. Baixe PostgreSQL 16 de https://www.postgresql.org/download/windows/
2. Instale normalmente
3. Instale a extensão pgvector:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```

### Criar Banco de Dados

```bash
# Conectar ao PostgreSQL
psql -U postgres

# Criar banco de dados
CREATE DATABASE eas_rag;

# Conectar ao banco
\c eas_rag

# Executar schema
\i database/schema.sql
```

Ou execute o schema.sql manualmente via pgAdmin ou DBeaver.

---

## Configuração do OpenRouter

### 1. Criar Conta

1. Acesse [openrouter.ai](https://openrouter.ai)
2. Crie uma conta
3. Vá em **Keys**
4. Clique em **Create Key**

### 2. Obter API Key

1. Copie a API Key gerada
2. Cole em `OPENROUTER_API_KEY` no `.env`

### 3. Modelos Disponíveis

| Modelo | Uso | Custo |
|--------|-----|-------|
| `openai/gpt-4o-mini` | Orquestração do scraper | Barato |
| `anthropic/claude-3.5-sonnet` | Análises complexas | Médio |
| `text-embedding-3-small` | Embeddings | Barato |

---

## Instalação Local

### 1. Clonar Projeto

```bash
git clone https://github.com/joaofilhosm/eas-rag-api.git
cd eas-rag-api
```

### 2. Criar Ambiente Virtual

```bash
# Linux/Mac
python -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
.\venv\Scripts\activate
```

### 3. Instalar Dependências

```bash
pip install -r requirements.txt
```

### 4. Configurar Variáveis de Ambiente

```bash
cp .env.example .env
```

Edite `.env`:

```env
# PostgreSQL
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/eas_rag
DB_USER=postgres
DB_PASSWORD=postgres
DB_NAME=eas_rag

# OpenRouter
OPENROUTER_API_KEY=sk-or-xxx
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
DEFAULT_MODEL=openai/gpt-4o-mini

# API Security
API_MASTER_KEY=sua-chave-master-secreta-aqui
```

### 5. Inicializar Banco de Dados

```bash
# Conectar ao PostgreSQL e executar
psql -U postgres -d eas_rag -f database/schema.sql
```

### 6. Executar

```bash
python run.py
```

Ou:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## Instalação com Docker

### 1. Build e Run

```bash
# Build
docker build -t eas-api .

# Run (com PostgreSQL externo)
docker run -d \
  --name eas-api \
  -p 8000:8000 \
  --env-file .env \
  eas-api
```

### 2. Com Docker Compose (Recomendado)

```bash
# Iniciar todos os serviços
docker-compose up -d

# Ver logs
docker-compose logs -f

# Parar
docker-compose down
```

### 3. Acessar Adminer (Opcional)

```bash
# Incluir perfil admin
docker-compose --profile admin up -d

# Acessar http://localhost:8080
# Sistema: PostgreSQL
# Servidor: postgres
# Usuário: postgres
# Senha: postgres
# Banco: eas_rag
```

---

## Variáveis de Ambiente

### Obrigatórias

| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| `DATABASE_URL` | URL de conexão PostgreSQL | `postgresql://user:pass@host:5432/db` |
| `OPENROUTER_API_KEY` | API Key OpenRouter | `sk-or-xxx` |
| `API_MASTER_KEY` | Master key para admin | `minha-chave-secreta` |

### Opcionais

| Variável | Default | Descrição |
|----------|---------|-----------|
| `DB_USER` | `postgres` | Usuário do banco |
| `DB_PASSWORD` | `postgres` | Senha do banco |
| `DB_NAME` | `eas_rag` | Nome do banco |
| `DB_PORT` | `5432` | Porta do banco |
| `OPENROUTER_BASE_URL` | `https://openrouter.ai/api/v1` | URL base |
| `DEFAULT_MODEL` | `openai/gpt-4o-mini` | Modelo LLM padrão |
| `FALLBACK_MODEL` | `anthropic/claude-3.5-sonnet` | Modelo fallback |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | Modelo de embedding |
| `HOST` | `0.0.0.0` | Host do servidor |
| `PORT` | `8000` | Porta do servidor |
| `DEBUG` | `true` | Modo debug |
| `SCRAPER_DELAY_SECONDS` | `2` | Delay entre requests |
| `API_KEY_EXPIRATION_DAYS` | `365` | Dias até expirar key |

---

## Testando a Instalação

### 1. Health Check

```bash
curl http://localhost:8000/api/v1/health
```

Resposta esperada:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00",
  "service": "EAS API RAG"
}
```

### 2. Criar API Key

```bash
curl -X POST http://localhost:8000/api/v1/api-keys \
  -H "X-Master-Key: sua-master-key" \
  -H "Content-Type: application/json" \
  -d '{"name": "Teste"}'
```

Resposta:
```json
{
  "id": "uuid",
  "name": "Teste",
  "key": "eas_abc123..."  // GUARDE ESTA KEY!
}
```

### 3. Testar Busca

```bash
curl -X POST http://localhost:8000/api/v1/search \
  -H "X-API-Key: eas_abc123..." \
  -H "Content-Type: application/json" \
  -d '{"query": "teste", "limit": 5}'
```

### 4. Acessar Documentação

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## Troubleshooting

### Erro: "Connection refused" ao conectar ao PostgreSQL

**Causa**: PostgreSQL não está rodando ou porta incorreta.

**Solução**:
```bash
# Verificar se PostgreSQL está rodando
sudo systemctl status postgresql  # Linux
# ou
docker ps | grep postgres         # Docker

# Verificar porta
netstat -an | grep 5432
```

### Erro: "extension vector does not exist"

**Causa**: pgvector não está instalado.

**Solução**:
```sql
-- Conectar ao banco
\c eas_rag

-- Criar extensão
CREATE EXTENSION IF NOT EXISTS vector;
```

### Erro: "Invalid API Key"

**Causa**: API Key incorreta ou expirada.

**Solução**:
1. Crie uma nova API Key
2. Verifique se está usando `X-API-Key` no header
3. Confirme que a key não expirou

### Erro: "Embedding generation failed"

**Causa**: Problema com OpenRouter/OpenAI.

**Solução**:
1. Verifique `OPENROUTER_API_KEY`
2. Confirme saldo/limite da conta
3. Teste manual:
   ```bash
   curl https://openrouter.ai/api/v1/embeddings \
     -H "Authorization: Bearer sk-or-xxx" \
     -H "Content-Type: application/json" \
     -d '{"model": "text-embedding-3-small", "input": "teste"}'
   ```

### Erro: "Port 8000 already in use"

**Causa**: Outro processo usando a porta.

**Solução**:
```bash
# Encontrar processo
lsof -i :8000  # Linux/Mac
netstat -ano | findstr :8000  # Windows

# Matar processo ou usar outra porta
uvicorn app.main:app --port 8001
```

### Docker Compose não inicia

**Causa**: Conflito de portas ou volumes.

**Solução**:
```bash
# Parar todos containers
docker-compose down -v

# Rebuild
docker-compose build --no-cache

# Iniciar
docker-compose up -d
```

---

## Próximos Passos

1. ✅ Instalação concluída
2. 📝 Leia a [Documentação da API](API.md)
3. 🤖 Use o [Prompt para Lovable](lovable_prompt.md)
4. 🚀 Configure scraping das fontes desejadas
5. 📊 Integre com sua aplicação

---

## Suporte

Para problemas não resolvidos:
1. Verifique os logs: `docker logs eas-api -f`
2. Abra uma issue no repositório
3. Consulte a documentação oficial do PostgreSQL/pgvector