"""
Serviço RAG (Retrieval Augmented Generation).
"""
from typing import List, Optional, Dict, Any
from openai import AsyncOpenAI

from app.config import get_settings
from app.services.embeddings import embedding_service
from database.supabase_client import db


class RAGService:
    """Serviço para busca semântica e RAG."""

    def __init__(self):
        settings = get_settings()
        self.client = AsyncOpenAI(
            base_url=settings.openrouter_base_url,
            api_key=settings.openrouter_api_key
        )
        self.default_model = settings.default_model
        self.embedding_service = embedding_service

    async def search(
        self,
        query: str,
        limit: int = 10,
        offset: int = 0,
        categoria: Optional[str] = None,
        tags: Optional[List[str]] = None,
        min_similarity: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Busca semântica na base de conhecimento.

        Args:
            query: Texto da busca
            limit: Número máximo de resultados
            offset: Offset para paginação
            categoria: Filtrar por categoria
            tags: Filtrar por tags
            min_similarity: Similaridade mínima

        Returns:
            Lista de resultados com similaridade
        """
        # Gera embedding da query
        query_embedding = await self.embedding_service.generate_embedding(query)

        # Busca usando função SQL do Supabase
        try:
            # Chamada RPC para função de busca
            result = await db.client.rpc(
                "search_knowledge",
                {
                    "query_embedding": query_embedding,
                    "limit_count": limit,
                    "min_similarity": min_similarity,
                    "filter_category": categoria,
                    "filter_tags": tags
                }
            ).execute()

            # Log da busca
            await db.create_search_log(
                query=query,
                results_count=len(result.data) if result.data else 0,
                avg_similarity=sum(r.get("similarity", 0) for r in result.data) / len(result.data) if result.data else 0,
                search_type="semantic"
            )

            return result.data if result.data else []

        except Exception as e:
            # Fallback para busca keyword se função não existir
            return await self._keyword_search(query, limit, categoria)

    async def _keyword_search(
        self,
        query: str,
        limit: int = 10,
        categoria: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Busca por palavras-chave (fallback).

        Args:
            query: Texto da busca
            limit: Número máximo de resultados
            categoria: Filtrar por categoria

        Returns:
            Lista de resultados
        """
        # Busca simples por texto
        search_query = db.client.table("knowledge_base").select("*")

        if categoria:
            search_query = search_query.eq("categoria", categoria)

        # Busca no título e conteúdo
        search_query = search_query.or_(f"titulo.ilike.%{query}%,conteudo.ilike.%{query}%")
        search_query = search_query.limit(limit)

        result = await search_query.execute()

        # Log da busca
        await db.create_search_log(
            query=query,
            results_count=len(result.data) if result.data else 0,
            search_type="keyword"
        )

        # Adiciona similarity fake para compatibilidade
        results = []
        for item in (result.data or []):
            item["similarity"] = 0.5  # Similaridade padrão para keyword
            results.append(item)

        return results

    async def find_similar(
        self,
        knowledge_id: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Encontra documentos similares a um conhecimento.

        Args:
            knowledge_id: ID do conhecimento
            limit: Número máximo de resultados

        Returns:
            Lista de documentos similares
        """
        # Busca embedding do conhecimento
        embedding_data = await db.get_embedding(knowledge_id)

        if not embedding_data:
            raise ValueError("Knowledge has no embedding")

        embedding = embedding_data["embedding"]

        # Busca similares
        result = await db.client.rpc(
            "search_knowledge",
            {
                "query_embedding": embedding,
                "limit_count": limit + 1,  # +1 para excluir o próprio documento
                "min_similarity": 0.3
            }
        ).execute()

        # Remove o próprio documento da lista
        similar_docs = [
            doc for doc in (result.data or [])
            if doc.get("id") != knowledge_id
        ][:limit]

        return similar_docs

    async def get_suggestions(
        self,
        prefix: str,
        limit: int = 10
    ) -> List[str]:
        """
        Retorna sugestões de busca baseadas no prefixo.

        Args:
            prefix: Prefixo para busca
            limit: Número máximo de sugestões

        Returns:
            Lista de sugestões
        """
        # Busca títulos que começam com o prefixo
        result = await db.client.table("knowledge_base").select("titulo").ilike("titulo", f"{prefix}%").limit(limit).execute()

        suggestions = [item["titulo"] for item in (result.data or [])]

        return suggestions

    async def generate_answer(
        self,
        query: str,
        context_limit: int = 5
    ) -> Dict[str, Any]:
        """
        Gera resposta usando RAG completo.

        Busca contexto relevante e gera resposta usando LLM.

        Args:
            query: Pergunta do usuário
            context_limit: Número de documentos de contexto

        Returns:
            Resposta gerada com contexto
        """
        # Busca contexto relevante
        context_docs = await self.search(query, limit=context_limit)

        if not context_docs:
            return {
                "answer": "Desculpe, não encontrei informações relevantes na base de conhecimento.",
                "context": [],
                "model": None
            }

        # Prepara contexto
        context_text = "\n\n".join([
            f"Título: {doc['titulo']}\nConteúdo: {doc['conteudo'][:500]}..."
            for doc in context_docs
        ])

        # Gera resposta usando LLM
        settings = get_settings()

        prompt = f"""Você é um assistente especializado em fitness, hipertrofia, nutrição e saúde.

Use APENAS as informações do contexto abaixo para responder à pergunta do usuário.
Se a informação não estiver no contexto, diga que não encontrou informações relevantes.

CONTEXTO:
{context_text}

PERGUNTA: {query}

Responda de forma clara e objetiva, citando as fontes quando relevante."""

        try:
            response = await self.client.chat.completions.create(
                model=self.default_model,
                messages=[
                    {"role": "system", "content": "Você é um assistente especializado em fitness, nutrição e saúde."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.7
            )

            answer = response.choices[0].message.content

        except Exception as e:
            answer = f"Erro ao gerar resposta: {str(e)}"

        return {
            "answer": answer,
            "context": [
                {
                    "titulo": doc["titulo"],
                    "categoria": doc.get("categoria"),
                    "url": doc.get("url_original")
                }
                for doc in context_docs
            ],
            "model": self.default_model
        }


# Instância global
rag_service = RAGService()