"""
Cliente Supabase para a API EAS.
"""
import os
from typing import Optional, List, Dict, Any
from functools import lru_cache
from supabase import create_client, Client
from app.config import get_settings


@lru_cache()
def get_supabase_client() -> Client:
    """
    Retorna cliente Supabase cached.

    Returns:
        Cliente Supabase configurado
    """
    settings = get_settings()
    return create_client(
        settings.supabase_url,
        settings.supabase_service_key  # Usa service role para operações admin
    )


# Cliente global para uso em módulos
supabase = get_supabase_client()


class DatabaseService:
    """Serviço de operações com banco de dados."""

    def __init__(self, client: Optional[Client] = None):
        """
        Inicializa o serviço.

        Args:
            client: Cliente Supabase (opcional, usa o global se não fornecido)
        """
        self.client = client or supabase

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
        data = {
            "key_hash": key_hash,
            "name": name,
            "description": description,
            "email": email,
            "expires_at": expires_at,
            "is_active": True
        }
        result = self.client.table("api_keys").insert(data).execute()
        return result.data[0] if result.data else None

    async def get_api_key_by_hash(self, key_hash: str) -> Optional[Dict[str, Any]]:
        """Busca API Key por hash."""
        result = self.client.table("api_keys").select("*").eq("key_hash", key_hash).execute()
        return result.data[0] if result.data else None

    async def list_api_keys(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """Lista todas as API Keys."""
        query = self.client.table("api_keys").select("*")
        if active_only:
            query = query.eq("is_active", True)
        result = query.order("created_at", desc=True).execute()
        return result.data

    async def deactivate_api_key(self, key_hash: str) -> bool:
        """Desativa uma API Key."""
        result = self.client.table("api_keys").update({"is_active": False}).eq("key_hash", key_hash).execute()
        return len(result.data) > 0

    async def update_last_used(self, key_hash: str) -> None:
        """Atualiza último uso da API Key."""
        self.client.table("api_keys").update({"last_used_at": "NOW()"}).eq("key_hash", key_hash).execute()

    # ================================================
    # Sources
    # ================================================

    async def create_source(
        self,
        name: str,
        url: str,
        type: str = "general",
        scrape_frequency_hours: int = 24,
        config: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Cria nova fonte de dados."""
        data = {
            "name": name,
            "url": url,
            "type": type,
            "scrape_frequency_hours": scrape_frequency_hours,
            "config": config or {},
            "is_active": True
        }
        result = self.client.table("sources").insert(data).execute()
        return result.data[0] if result.data else None

    async def get_source(self, source_id: str) -> Optional[Dict[str, Any]]:
        """Busca fonte por ID."""
        result = self.client.table("sources").select("*").eq("id", source_id).execute()
        return result.data[0] if result.data else None

    async def get_sources(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """Lista todas as fontes."""
        query = self.client.table("sources").select("*")
        if active_only:
            query = query.eq("is_active", True)
        result = query.order("created_at", desc=True).execute()
        return result.data

    async def update_source_last_scraped(self, source_id: str) -> None:
        """Atualiza último scraping da fonte."""
        self.client.table("sources").update({"last_scraped_at": "NOW()"}).eq("id", source_id).execute()

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
        data = {
            "titulo": titulo,
            "conteudo": conteudo,
            "source_id": source_id,
            "categoria": categoria,
            "tags": tags or [],
            "url_original": url_original,
            "metadata": metadata or {},
            "embedding_status": "pending"
        }
        result = self.client.table("knowledge_base").insert(data).execute()
        return result.data[0] if result.data else None

    async def get_knowledge(self, knowledge_id: str) -> Optional[Dict[str, Any]]:
        """Busca conhecimento por ID."""
        result = self.client.table("knowledge_base").select("*").eq("id", knowledge_id).execute()
        return result.data[0] if result.data else None

    async def list_knowledge(
        self,
        limit: int = 50,
        offset: int = 0,
        categoria: Optional[str] = None,
        source_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Lista conhecimentos com filtros."""
        query = self.client.table("knowledge_base").select("*")

        if categoria:
            query = query.eq("categoria", categoria)
        if source_id:
            query = query.eq("source_id", source_id)

        result = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
        return result.data

    async def delete_knowledge(self, knowledge_id: str) -> bool:
        """Deleta conhecimento."""
        result = self.client.table("knowledge_base").delete().eq("id", knowledge_id).execute()
        return len(result.data) > 0

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
        data = {
            "knowledge_id": knowledge_id,
            "embedding": embedding,
            "model": model
        }
        result = self.client.table("embeddings").insert(data).execute()

        # Atualiza status do conhecimento
        self.client.table("knowledge_base").update({"embedding_status": "done"}).eq("id", knowledge_id).execute()

        return result.data[0] if result.data else None

    async def get_embedding(self, knowledge_id: str) -> Optional[Dict[str, Any]]:
        """Busca embedding por knowledge_id."""
        result = self.client.table("embeddings").select("*").eq("knowledge_id", knowledge_id).execute()
        return result.data[0] if result.data else None

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
        data = {
            "source_id": source_id,
            "status": status,
            "items_extracted": items_extracted,
            "items_failed": items_failed,
            "error_message": error_message,
            "started_at": started_at,
            "completed_at": completed_at,
            "duration_seconds": duration_seconds
        }
        result = self.client.table("scrape_logs").insert(data).execute()
        return result.data[0] if result.data else None

    async def get_scrape_logs(
        self,
        source_id: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Lista logs de scraping."""
        query = self.client.table("scrape_logs").select("*, sources(name)")
        if source_id:
            query = query.eq("source_id", source_id)
        result = query.order("started_at", desc=True).limit(limit).execute()
        return result.data

    # ================================================
    # Search Logs
    # ================================================

    async def create_search_log(
        self,
        query: str,
        results_count: int,
        avg_similarity: Optional[float] = None,
        search_type: str = "semantic",
        api_key_id: Optional[str] = None
    ) -> None:
        """Cria log de busca."""
        data = {
            "query": query,
            "results_count": results_count,
            "avg_similarity": avg_similarity,
            "search_type": search_type,
            "api_key_id": api_key_id
        }
        self.client.table("search_logs").insert(data).execute()

    # ================================================
    # Stats
    # ================================================

    async def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas gerais."""
        result = self.client.table("v_stats").select("*").execute()
        return result.data[0] if result.data else {}


# Instância global do serviço
db = DatabaseService()