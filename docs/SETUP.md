# Guia de Instalação - EAS API RAG

## Índice

1. [Pré-requisitos](#pré-requisitos)
2. [Configuração do Supabase](#configuração-do-supabase)
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
- **Conta no Supabase** (gratuita) - [supabase.com](https://supabase.com)
- **Conta no OpenRouter** (ou OpenAI) - [openrouter.ai](https://openrouter.ai)

### Opcionais

- **Docker** e **Docker Compose** (para containerização)
- **Git** (para versionamento)

---

## Configuração do Supabase

### 1. Criar Projeto

1. Acesse [supabase.com](https://supabase.com)
2. Clique em "New Project"
3. Preencha:
   - **Name**: `eas-rag-db`
   - **Database Password**: (anote bem!)
   - **Region**: Escolha a mais próxima

### 2. Obter Credenciais

1. No dashboard, vá em **Settings** > **API**
2. Copie:
   - **Project URL** → `SUPABASE_URL`
   - **anon public** → `SUPABASE_KEY`
   - **service_role** → `SUPABASE_SERVICE_KEY` (⚠️ Mantenha secreta!)

### 3. Executar Schema SQL

1. Vá em **SQL Editor**
2. Crie uma nova query
3. Cole o conteúdo de `database/schema.sql`
4. Execute (Play button)

```sql
-- Verificar se funcionou
SELECT * FROM sources;
SELECT * FROM api_keys LIMIT 1;
```

### 4. Habilitar pgvector

O schema já inclui `CREATE EXTENSION IF NOT EXISTS vector`, mas você pode verificar:

```sql
SELECT * FROM pg_extension WHERE extname = 'vector';
```

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

### 1. Clonar/Copiar Projeto

```bash
cd eas
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
# Supabase
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# OpenRouter
OPENROUTER_API_KEY=sk-or-xxx
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
DEFAULT_MODEL=openai/gpt-4o-mini

# API Security
API_MASTER_KEY=sua-chave-master-secreta-aqui
```

### 5. Executar

```bash
python run.py
```

Ou:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## Instalação com Docker

### 1. Build da Imagem

```bash
docker build -t eas-api .
```

### 2. Executar Container

```bash
docker run -d \
  --name eas-api \
  -p 8000:8000 \
  --env-file .env \
  eas-api
```

### 3. Com Docker Compose

```bash
docker-compose up -d
```

### 4. Verificar Logs

```bash
docker logs eas-api -f
```

---

## Variáveis de Ambiente

### Obrigatórias

| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| `SUPABASE_URL` | URL do projeto Supabase | `https://xxx.supabase.co` |
| `SUPABASE_KEY` | Chave anon/public | `eyJhbGciOiJI...` |
| `SUPABASE_SERVICE_KEY` | Chave service role | `eyJhbGciOiJI...` |
| `OPENROUTER_API_KEY` | API Key OpenRouter | `sk-or-xxx` |
| `API_MASTER_KEY` | Master key para admin | `minha-chave-secreta` |

### Opcionais

| Variável | Default | Descrição |
|----------|---------|-----------|
| `OPENROUTER_BASE_URL` | `https://openrouter.ai/api/v1` | URL base |
| `DEFAULT_MODEL` | `openai/gpt-4o-mini` | Modelo LLM padrão |
| `FALLBACK_MODEL` | `anthropic/claude-3.5-sonnet` | Modelo fallback |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | Modelo de embedding |
| `EMBEDDING_DIMENSIONS` | `1536` | Dimensões do embedding |
| `HOST` | `0.0.0.0` | Host do servidor |
| `PORT` | `8000` | Porta do servidor |
| `DEBUG` | `true` | Modo debug |
| `SCRAPER_DELAY_SECONDS` | `2` | Delay entre requests |
| `SCRAPER_MAX_RETRIES` | `3` | Máximo de tentativas |
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

### Erro: "Failed to connect to Supabase"

**Causa**: Credenciais incorretas ou banco não acessível.

**Solução**:
1. Verifique `SUPABASE_URL` e `SUPABASE_KEY`
2. Confirme que o projeto Supabase está ativo
3. Teste conexão manual:
   ```bash
   curl https://xxx.supabase.co/rest/v1/ \
     -H "apikey: eyJhbGciOiJI..."
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

### Erro: "pgvector extension not found"

**Causa**: Extensão pgvector não instalada.

**Solução**:
1. Execute o schema SQL novamente
2. Verifique se o Supabase suporta pgvector (todos os planos suportam)

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

### Scraper não funciona

**Causa**: Sites podem bloquear requests ou mudar estrutura.

**Solução**:
1. Verifique logs do scraper
2. Teste URL manualmente
3. Atualize seletores CSS se necessário

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
3. Consulte a documentação oficial do Supabase/OpenRouter