"""
Serviço RAG (Retrieval Augmented Generation).
"""
from typing import List, Optional, Dict, Any
from openai import AsyncOpenAI

from app.config import get_settings
from app.services.embeddings import embedding_service
from database.database import db


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
        # Verifica se há embeddings na base
        try:
            embedding_count = await db.fetchval("SELECT COUNT(*) FROM embeddings")
            if embedding_count == 0:
                # Sem embeddings, usa busca por palavras-chave
                return await self._keyword_search(query, limit, categoria)
        except:
            pass

        # Gera embedding da query
        try:
            query_embedding = await self.embedding_service.generate_embedding(query)
        except:
            # Se falhar ao gerar embedding, usa keyword search
            return await self._keyword_search(query, limit, categoria)

        # Busca usando pgvector
        try:
            results = await db.search_similar(
                query_embedding=query_embedding,
                limit=limit,
                min_similarity=min_similarity,
                categoria=categoria,
                tags=tags
            )

            # Se não encontrou resultados, tenta keyword search
            if not results:
                return await self._keyword_search(query, limit, categoria)

            # Log da busca
            await db.execute(
                """
                INSERT INTO search_logs (query, results_count, avg_similarity, search_type)
                VALUES ($1, $2, $3, $4)
                """,
                query,
                len(results),
                sum(r.get("similarity", 0) for r in results) / len(results) if results else 0,
                "semantic"
            )

            return [
                {
                    "knowledge": {
                        "id": r["id"],
                        "titulo": r["titulo"],
                        "conteudo": r["conteudo"],
                        "categoria": r["categoria"],
                        "tags": r["tags"],
                        "url_original": r["url_original"],
                        "source_id": r.get("source_id"),
                        "created_at": r["created_at"].isoformat() if r.get("created_at") else None
                    },
                    "similarity": r.get("similarity", 0),
                    "embedding_used": True
                }
                for r in results
            ]

        except Exception as e:
            # Fallback para busca keyword se erro
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
        # Divide a query em palavras individuais para busca mais flexível
        words = [w.strip().lower() for w in query.split() if len(w.strip()) > 2]

        if not words:
            words = [query.lower()]

        # Cria condições para cada palavra (OR) e calcula relevância
        word_conditions = []
        params = []
        for i, word in enumerate(words[:5]):  # Limite de 5 palavras
            word_conditions.append(f"COALESCE((titulo ILIKE ${i+1})::int, 0) + COALESCE((conteudo ILIKE ${i+1})::int, 0)")
            params.append(f"%{word}%")

        relevance_expr = " + ".join(word_conditions)
        param_idx = len(params) + 1

        extra_conditions = ""
        if categoria:
            extra_conditions = f" AND categoria = ${param_idx}"
            params.append(categoria)
            param_idx += 1

        params.append(limit)

        query_sql = f"""
        SELECT *, ({relevance_expr}) as relevance_score
        FROM knowledge_base
        WHERE ({' OR '.join([f'titulo ILIKE ${i+1} OR conteudo ILIKE ${i+1}' for i in range(len(words[:5]))])})
        {extra_conditions}
        ORDER BY relevance_score DESC, created_at DESC
        LIMIT ${param_idx}
        """

        try:
            results = await db.fetch(query_sql, *params)
        except Exception as e:
            # Fallback simples se a query complexa falhar
            simple_query = """
            SELECT * FROM knowledge_base
            WHERE titulo ILIKE $1 OR conteudo ILIKE $1
            ORDER BY created_at DESC
            LIMIT $2
            """
            results = await db.fetch(simple_query, f"%{query}%", limit)

        # Log da busca
        try:
            await db.execute(
                """
                INSERT INTO search_logs (query, results_count, search_type)
                VALUES ($1, $2, $3)
                """,
                query,
                len(results),
                "keyword"
            )
        except:
            pass

        # Adiciona similarity fake para compatibilidade
        return [
            {
                "knowledge": {
                    "id": str(r["id"]),
                    "titulo": r["titulo"],
                    "conteudo": r["conteudo"],
                    "categoria": r["categoria"],
                    "tags": r["tags"],
                    "url_original": r["url_original"],
                    "created_at": r["created_at"].isoformat() if r.get("created_at") else None
                },
                "similarity": 0.5,  # Similaridade padrão para keyword
                "embedding_used": False
            }
            for r in results
        ]

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
        results = await db.search_similar(
            query_embedding=embedding,
            limit=limit + 1,  # +1 para excluir o próprio documento
            min_similarity=0.3
        )

        # Remove o próprio documento da lista
        similar_docs = [
            doc for doc in results
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
        results = await db.fetch(
            "SELECT titulo FROM knowledge_base WHERE titulo ILIKE $1 LIMIT $2",
            f"{prefix}%",
            limit
        )

        suggestions = [r["titulo"] for r in results]

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
            f"Título: {doc['knowledge']['titulo']}\nConteúdo: {doc['knowledge']['conteudo'][:500]}..."
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
                    "titulo": doc["knowledge"]["titulo"],
                    "categoria": doc["knowledge"].get("categoria"),
                    "url": doc["knowledge"].get("url_original")
                }
                for doc in context_docs
            ],
            "model": self.default_model
        }


# Instância global
rag_service = RAGService()