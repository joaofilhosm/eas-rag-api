"""
Cliente PostgreSQL com suporte a pgvector.
"""
import asyncpg
from typing import Optional, List, Dict, Any
from functools import lru_cache
import json

from app.config import get_settings


class Database:
    """Cliente PostgreSQL assíncrono com suporte a pgvector."""

    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        self.settings = get_settings()

    async def connect(self):
        """Cria pool de conexões com o banco."""
        if self.pool is None:
            self.pool = await asyncpg.create_pool(
                self.settings.database_url,
                min_size=5,
                max_size=self.settings.database_pool_size,
                command_timeout=60
            )
        return self.pool

    async def disconnect(self):
        """Fecha o pool de conexões."""
        if self.pool:
            await self.pool.close()
            self.pool = None

    async def execute(self, query: str, *args) -> str:
        """Executa query sem retorno."""
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)

    async def fetch(self, query: str, *args) -> List[asyncpg.Record]:
        """Executa query e retorna múltiplos registros."""
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def fetchrow(self, query: str, *args) -> Optional[asyncpg.Record]:
        """Executa query e retorna um registro."""
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def fetchval(self, query: str, *args) -> Any:
        """Executa query e retorna um valor."""
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, *args)

    # ================================================
    # API Keys
    # ================================================

    async def create_api_key(
        self,
        key_hash: str,
        name: str,
        description: Optional[str] = None,
        email: Optional[str] = None,
        expires_at: Optional[str] = None
    ) -> Dict[str, Any]:
        """Cria nova API Key."""
        query = """
        INSERT INTO api_keys (key_hash, name, description, email, expires_at)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING id, key_hash, name, description, email, is_active, created_at, expires_at
        """
        row = await self.fetchrow(query, key_hash, name, description, email, expires_at)
        return dict(row) if row else None

    async def get_api_key_by_hash(self, key_hash: str) -> Optional[Dict[str, Any]]:
        """Busca API Key por hash."""
        query = "SELECT * FROM api_keys WHERE key_hash = $1"
        row = await self.fetchrow(query, key_hash)
        return dict(row) if row else None

    async def list_api_keys(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """Lista todas as API Keys."""
        if active_only:
            query = "SELECT * FROM api_keys WHERE is_active = true ORDER BY created_at DESC"
        else:
            query = "SELECT * FROM api_keys ORDER BY created_at DESC"
        rows = await self.fetch(query)
        return [dict(row) for row in rows]

    async def deactivate_api_key(self, key_hash: str) -> bool:
        """Desativa uma API Key."""
        query = "UPDATE api_keys SET is_active = false WHERE key_hash = $1"
        result = await self.execute(query, key_hash)
        return "UPDATE 1" in result

    async def update_last_used(self, key_hash: str) -> None:
        """Atualiza último uso da API Key."""
        query = "UPDATE api_keys SET last_used_at = NOW() WHERE key_hash = $1"
        await self.execute(query, key_hash)

    # ================================================
    # Sources
    # ================================================

    async def create_source(
        self,
        name: str,
        url: str,
        source_type: str = "general",
        scrape_frequency_hours: int = 24,
        config: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Cria nova fonte de dados."""
        query = """
        INSERT INTO sources (name, url, type, scrape_frequency_hours, config)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING *
        """
        row = await self.fetchrow(query, name, url, source_type, scrape_frequency_hours, json.dumps(config or {}))
        return dict(row) if row else None

    async def get_source(self, source_id: str) -> Optional[Dict[str, Any]]:
        """Busca fonte por ID."""
        query = "SELECT * FROM sources WHERE id = $1"
        row = await self.fetchrow(query, source_id)
        return dict(row) if row else None

    async def get_sources(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """Lista todas as fontes."""
        if active_only:
            query = "SELECT * FROM sources WHERE is_active = true ORDER BY created_at DESC"
        else:
            query = "SELECT * FROM sources ORDER BY created_at DESC"
        rows = await self.fetch(query)
        return [dict(row) for row in rows]

    async def update_source_last_scraped(self, source_id: str) -> None:
        """Atualiza último scraping da fonte."""
        query = "UPDATE sources SET last_scraped_at = NOW() WHERE id = $1"
        await self.execute(query, source_id)

    # ================================================
    # Knowledge Base
    # ================================================

    async def create_knowledge(
        self,
        titulo: str,
        conteudo: str,
        source_id: Optional[str] = None,
        categoria: Optional[str] = None,
        tags: Optional[List[str]] = None,
        url_original: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Cria novo conhecimento."""
        query = """
        INSERT INTO knowledge_base (titulo, conteudo, source_id, categoria, tags, url_original, metadata)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        RETURNING *
        """
        row = await self.fetchrow(
            query, titulo, conteudo, source_id, categoria, tags or [], url_original, json.dumps(metadata or {})
        )
        return dict(row) if row else None

    async def get_knowledge(self, knowledge_id: str) -> Optional[Dict[str, Any]]:
        """Busca conhecimento por ID."""
        query = "SELECT * FROM knowledge_base WHERE id = $1"
        row = await self.fetchrow(query, knowledge_id)
        return dict(row) if row else None

    async def list_knowledge(
        self,
        limit: int = 50,
        offset: int = 0,
        categoria: Optional[str] = None,
        source_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Lista conhecimentos com filtros."""
        conditions = []
        params = []
        param_idx = 1

        if categoria:
            conditions.append(f"categoria = ${param_idx}")
            params.append(categoria)
            param_idx += 1

        if source_id:
            conditions.append(f"source_id = ${param_idx}")
            params.append(source_id)
            param_idx += 1

        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

        query = f"""
        SELECT * FROM knowledge_base
        {where_clause}
        ORDER BY created_at DESC
        LIMIT ${param_idx} OFFSET ${param_idx + 1}
        """
        params.extend([limit, offset])

        rows = await self.fetch(query, *params)
        return [dict(row) for row in rows]

    async def delete_knowledge(self, knowledge_id: str) -> bool:
        """Deleta conhecimento."""
        query = "DELETE FROM knowledge_base WHERE id = $1 RETURNING id"
        result = await self.fetchval(query, knowledge_id)
        return result is not None

    # ================================================
    # Embeddings
    # ================================================

    async def create_embedding(
        self,
        knowledge_id: str,
        embedding: List[float],
        model: str = "text-embedding-3-small"
    ) -> Dict[str, Any]:
        """Cria embedding para conhecimento."""
        query = """
        INSERT INTO embeddings (knowledge_id, embedding, model)
        VALUES ($1, $2, $3)
        RETURNING *
        """
        # Converte lista para string de vector
        vector_str = "[" + ",".join(str(x) for x in embedding) + "]"
        row = await self.fetchrow(query, knowledge_id, vector_str, model)

        # Atualiza status do conhecimento
        await self.execute(
            "UPDATE knowledge_base SET embedding_status = 'done' WHERE id = $1",
            knowledge_id
        )

        return dict(row) if row else None

    async def get_embedding(self, knowledge_id: str) -> Optional[Dict[str, Any]]:
        """Busca embedding por knowledge_id."""
        query = "SELECT * FROM embeddings WHERE knowledge_id = $1"
        row = await self.fetchrow(query, knowledge_id)
        return dict(row) if row else None

    async def search_similar(
        self,
        query_embedding: List[float],
        limit: int = 10,
        min_similarity: float = 0.5,
        categoria: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Busca vetorial por similaridade."""
        vector_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

        conditions = ["1 - (e.embedding <=> $1::vector) >= $2"]
        params = [vector_str, min_similarity]
        param_idx = 3

        if categoria:
            conditions.append(f"kb.categoria = ${param_idx}")
            params.append(categoria)
            param_idx += 1

        if tags:
            conditions.append(f"kb.tags && ${param_idx}")
            params.append(tags)
            param_idx += 1

        where_clause = " AND ".join(conditions)
        params.append(limit)

        query = f"""
        SELECT
            kb.id,
            kb.titulo,
            kb.conteudo,
            kb.categoria,
            kb.tags,
            kb.url_original,
            kb.source_id,
            kb.created_at,
            1 - (e.embedding <=> $1::vector) as similarity
        FROM knowledge_base kb
        JOIN embeddings e ON kb.id = e.knowledge_id
        WHERE {where_clause}
        ORDER BY e.embedding <=> $1::vector
        LIMIT ${param_idx}
        """

        rows = await self.fetch(query, *params)
        return [dict(row) for row in rows]

    # ================================================
    # Scrape Logs
    # ================================================

    async def create_scrape_log(
        self,
        source_id: str,
        status: str,
        items_extracted: int = 0,
        items_failed: int = 0,
        error_message: Optional[str] = None,
        started_at: Optional[str] = None,
        completed_at: Optional[str] = None,
        duration_seconds: Optional[float] = None
    ) -> Dict[str, Any]:
        """Cria log de scraping."""
        query = """
        INSERT INTO scrape_logs (source_id, status, items_extracted, items_failed, error_message, started_at, completed_at, duration_seconds)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        RETURNING *
        """
        row = await self.fetchrow(
            query, source_id, status, items_extracted, items_failed,
            error_message, started_at, completed_at, duration_seconds
        )
        return dict(row) if row else None

    async def get_scrape_logs(
        self,
        source_id: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Lista logs de scraping."""
        if source_id:
            query = """
            SELECT sl.*, s.name as source_name
            FROM scrape_logs sl
            JOIN sources s ON sl.source_id = s.id
            WHERE sl.source_id = $1
            ORDER BY sl.started_at DESC
            LIMIT $2
            """
            rows = await self.fetch(query, source_id, limit)
        else:
            query = """
            SELECT sl.*, s.name as source_name
            FROM scrape_logs sl
            JOIN sources s ON sl.source_id = s.id
            ORDER BY sl.started_at DESC
            LIMIT $1
            """
            rows = await self.fetch(query, limit)

        return [dict(row) for row in rows]

    # ================================================
    # Stats
    # ================================================

    async def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas gerais."""
        stats = {}

        # Total de conhecimentos
        stats["total_knowledge"] = await self.fetchval("SELECT COUNT(*) FROM knowledge_base")

        # Total de embeddings
        stats["total_embeddings"] = await self.fetchval("SELECT COUNT(*) FROM embeddings")

        # Fontes ativas
        stats["active_sources"] = await self.fetchval("SELECT COUNT(*) FROM sources WHERE is_active = true")

        # API Keys ativas
        stats["active_api_keys"] = await self.fetchval("SELECT COUNT(*) FROM api_keys WHERE is_active = true")

        # Último conhecimento adicionado
        last = await self.fetchrow("SELECT created_at FROM knowledge_base ORDER BY created_at DESC LIMIT 1")
        stats["last_knowledge_added"] = last["created_at"] if last else None

        # Último scraping
        last_scrape = await self.fetchrow("SELECT started_at FROM scrape_logs ORDER BY started_at DESC LIMIT 1")
        stats["last_scrape_run"] = last_scrape["started_at"] if last_scrape else None

        return stats

    # ================================================
    # Setup / Migrations
    # ================================================

    async def init_db(self):
        """Inicializa o banco de dados (cria tabelas)."""
        # Lê o schema SQL
        import os
        schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
        with open(schema_path, "r", encoding="utf-8") as f:
            schema_sql = f.read()

        # Executa o schema
        await self.execute(schema_sql)
        print("✓ Banco de dados inicializado")


# Instância global
db = Database()


@lru_cache()
def get_database() -> Database:
    """Retorna instância do banco (cached)."""
    return db


# Função para obter conexão (dependency injection)
async def get_db():
    """Dependency para FastAPI."""
    if db.pool is None:
        await db.connect()
    return db