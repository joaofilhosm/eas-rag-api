# Documentação da API EAS

## Base URL

```
http://localhost:8000/api/v1
```

## Autenticação

### API Key

A maioria dos endpoints requer autenticação via API Key.

**Header:**
```
X-API-Key: eas_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### Master Key

Endpoints administrativos requerem a Master Key.

**Header:**
```
X-Master-Key: sua-master-key
```

---

## Health Check

### GET /health

Retorna status básico da API.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00",
  "service": "EAS API RAG"
}
```

### GET /health/detailed

Retorna status detalhado incluindo conexão com banco de dados.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00",
  "services": {
    "database": {
      "status": "healthy",
      "stats": {
        "total_knowledge": 1234,
        "active_sources": 5,
        "total_embeddings": 1234
      }
    }
  }
}
```

### GET /stats

Retorna estatísticas gerais da API.

**Response:**
```json
{
  "success": true,
  "data": {
    "total_knowledge": 1234,
    "active_sources": 5,
    "active_api_keys": 10,
    "total_embeddings": 1234,
    "last_knowledge_added": "2024-01-15T10:00:00",
    "last_scrape_run": "2024-01-15T09:00:00"
  }
}
```

---

## API Keys

### POST /api-keys

Cria uma nova API Key.

**Headers:**
- `X-Master-Key`: Master Key

**Body:**
```json
{
  "name": "Nome da Aplicação",
  "description": "Descrição opcional",
  "email": "user@example.com",
  "expires_at": "2025-12-31T23:59:59"
}
```

**Response:**
```json
{
  "id": "uuid",
  "name": "Nome da Aplicação",
  "key": "eas_abc123def456... (GUARDE COM CUIDADO)",
  "key_hash": "md5_hash",
  "is_active": true,
  "created_at": "2024-01-15T10:30:00",
  "expires_at": "2025-12-31T23:59:59"
}
```

⚠️ **Importante**: A API Key completa só é mostrada uma vez na criação!

### GET /api-keys

Lista todas as API Keys.

**Headers:**
- `X-Master-Key`: Master Key

**Query Params:**
- `active_only` (bool): Filtrar apenas keys ativas (default: true)

**Response:**
```json
[
  {
    "id": "uuid",
    "name": "Nome da Aplicação",
    "description": "Descrição",
    "is_active": true,
    "created_at": "2024-01-15T10:30:00",
    "expires_at": "2025-12-31T23:59:59",
    "last_used_at": "2024-01-15T11:00:00"
  }
]
```

### DELETE /api-keys/{id}

Desativa uma API Key.

**Headers:**
- `X-Master-Key`: Master Key

**Response:**
```json
{
  "success": true,
  "message": "API key deactivated"
}
```

---

## Busca (Search)

### POST /search

Busca semântica na base de conhecimento.

**Headers:**
- `X-API-Key`: API Key válida

**Body:**
```json
{
  "query": "efeitos de esteroides anabolizantes no corpo",
  "limit": 10,
  "offset": 0,
  "categoria": "esteroides",
  "tags": ["anabolizantes", "hormônios"],
  "min_similarity": 0.5
}
```

**Response:**
```json
{
  "results": [
    {
      "knowledge": {
        "id": "uuid",
        "titulo": "Efeitos dos Esteroides Anabolizantes",
        "conteudo": "Conteúdo completo...",
        "categoria": "esteroides",
        "tags": ["anabolizantes", "hormônios"],
        "url_original": "https://...",
        "created_at": "2024-01-15T10:00:00"
      },
      "similarity": 0.92,
      "embedding_used": true
    }
  ],
  "total": 5,
  "query": "efeitos de esteroides anabolizantes no corpo",
  "limit": 10,
  "offset": 0,
  "search_type": "semantic"
}
```

### POST /search/similar/{knowledge_id}

Encontra documentos similares a um conhecimento.

**Headers:**
- `X-API-Key`: API Key válida

**Path Params:**
- `knowledge_id`: ID do conhecimento

**Query Params:**
- `limit`: Número máximo de resultados (default: 5)

**Response:**
```json
{
  "success": true,
  "results": [
    {
      "id": "uuid",
      "titulo": "Título similar",
      "conteudo": "Conteúdo...",
      "similarity": 0.85
    }
  ],
  "total": 3
}
```

### GET /search/suggestions

Retorna sugestões de busca baseadas no prefixo.

**Headers:**
- `X-API-Key`: API Key válida

**Query Params:**
- `prefix`: Prefixo para busca
- `limit`: Número máximo de sugestões (default: 10)

**Response:**
```json
{
  "success": true,
  "suggestions": [
    "Efeitos de esteroides anabolizantes",
    "Esteroides e hipertrofia muscular",
    "Esteroides orais vs injetáveis"
  ]
}
```

---

## Knowledge Base

### POST /knowledge

Cria novo conhecimento.

**Headers:**
- `X-Master-Key`: Master Key

**Body:**
```json
{
  "titulo": "Título do Conhecimento",
  "conteudo": "Conteúdo completo do conhecimento...",
  "source_id": "uuid (opcional)",
  "categoria": "treino",
  "tags": ["tag1", "tag2"],
  "url_original": "https://...",
  "metadata": {
    "autor": "Autor",
    "data": "2024-01-15"
  }
}
```

**Response:**
```json
{
  "id": "uuid",
  "titulo": "Título do Conhecimento",
  "conteudo": "Conteúdo completo...",
  "categoria": "treino",
  "tags": ["tag1", "tag2"],
  "url_original": "https://...",
  "created_at": "2024-01-15T10:30:00",
  "updated_at": "2024-01-15T10:30:00"
}
```

### GET /knowledge

Lista conhecimentos com filtros.

**Headers:**
- `X-API-Key`: API Key válida

**Query Params:**
- `limit`: Número máximo de resultados (default: 50)
- `offset`: Offset para paginação (default: 0)
- `categoria`: Filtrar por categoria
- `source_id`: Filtrar por fonte

**Response:**
```json
[
  {
    "id": "uuid",
    "titulo": "Título",
    "conteudo": "Conteúdo...",
    "categoria": "treino",
    "tags": ["tag1"],
    "created_at": "2024-01-15T10:00:00"
  }
]
```

### GET /knowledge/{id}

Busca conhecimento por ID.

**Headers:**
- `X-API-Key`: API Key válida

**Response:**
```json
{
  "id": "uuid",
  "titulo": "Título",
  "conteudo": "Conteúdo completo...",
  "categoria": "treino",
  "tags": ["tag1", "tag2"],
  "url_original": "https://...",
  "metadata": {},
  "created_at": "2024-01-15T10:00:00",
  "updated_at": "2024-01-15T10:00:00"
}
```

### PUT /knowledge/{id}

Atualiza conhecimento existente.

**Headers:**
- `X-Master-Key`: Master Key

**Body:**
```json
{
  "titulo": "Novo título",
  "conteudo": "Novo conteúdo",
  "tags": ["nova_tag"]
}
```

### DELETE /knowledge/{id}

Deleta conhecimento.

**Headers:**
- `X-Master-Key`: Master Key

**Response:**
```json
{
  "success": true,
  "message": "Knowledge deleted"
}
```

### GET /categories

Lista todas as categorias disponíveis.

**Headers:**
- `X-API-Key`: API Key válida

**Response:**
```json
{
  "success": true,
  "categories": [
    "treino",
    "nutricao",
    "suplementacao",
    "hormonios",
    "esteroides",
    "medico",
    "cientifico",
    "tecnico",
    "geral"
  ]
}
```

---

## Scraper

### GET /scraper/status

Retorna status atual do scraper.

**Headers:**
- `X-Master-Key`: Master Key

**Response:**
```json
{
  "is_running": false,
  "current_source": null,
  "last_run_at": "2024-01-15T09:00:00",
  "last_status": "success",
  "total_items": 1234,
  "sources_active": 5,
  "sources_pending": 2
}
```

### POST /scraper/start

Inicia scraping manual.

**Headers:**
- `X-Master-Key`: Master Key

**Body:**
```json
{
  "source_ids": ["uuid1", "uuid2"],
  "force": false
}
```

**Response:**
```json
{
  "success": true,
  "message": "Scraper started",
  "source_ids": ["uuid1", "uuid2"],
  "force": false
}
```

### POST /scraper/stop

Para o scraper em execução.

**Headers:**
- `X-Master-Key`: Master Key

**Response:**
```json
{
  "success": true,
  "message": "Scraper stopped"
}
```

### GET /scraper/logs

Lista logs de scraping.

**Headers:**
- `X-Master-Key`: Master Key

**Query Params:**
- `source_id`: Filtrar por fonte
- `limit`: Número máximo de logs

**Response:**
```json
[
  {
    "id": "uuid",
    "source_id": "uuid",
    "status": "success",
    "items_extracted": 50,
    "items_failed": 2,
    "started_at": "2024-01-15T09:00:00",
    "completed_at": "2024-01-15T09:30:00",
    "duration_seconds": 1800
  }
]
```

---

## Sources (Fontes de Dados)

### GET /sources

Lista todas as fontes de dados.

**Headers:**
- `X-Master-Key`: Master Key

**Query Params:**
- `active_only`: Filtrar apenas ativas (default: true)

**Response:**
```json
[
  {
    "id": "uuid",
    "name": "Dicas de Treino",
    "url": "https://www.dicasdetreino.com.br",
    "type": "fitness",
    "is_active": true,
    "last_scraped_at": "2024-01-15T09:00:00",
    "scrape_frequency_hours": 24,
    "total_items": 500
  }
]
```

### POST /sources

Cria nova fonte de dados.

**Headers:**
- `X-Master-Key`: Master Key

**Body:**
```json
{
  "name": "Nova Fonte",
  "url": "https://exemplo.com",
  "type": "fitness",
  "scrape_frequency_hours": 24
}
```

**Response:**
```json
{
  "id": "uuid",
  "name": "Nova Fonte",
  "url": "https://exemplo.com",
  "type": "fitness",
  "is_active": true,
  "created_at": "2024-01-15T10:30:00"
}
```

### PUT /sources/{id}/deactivate

Desativa uma fonte.

**Headers:**
- `X-Master-Key`: Master Key

**Response:**
```json
{
  "success": true,
  "message": "Source deactivated"
}
```

---

## Códigos de Erro

| Código | Descrição |
|--------|-----------|
| 200 | Sucesso |
| 201 | Criado |
| 400 | Requisição inválida |
| 401 | Não autorizado (API Key inválida) |
| 403 | Proibido (sem permissão) |
| 404 | Não encontrado |
| 409 | Conflito (ex: scraper já rodando) |
| 422 | Dados inválidos |
| 500 | Erro interno do servidor |

---

## Rate Limiting

Por padrão, não há rate limiting implementado. Considere adicionar em produção.

---

## Webhooks (Futuro)

Em breve suporte a webhooks para notificações de:
- Scraping concluído
- Novo conhecimento adicionado
- Erros do sistema