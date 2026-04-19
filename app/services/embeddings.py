"""
Serviço de Embeddings usando OpenRouter (compatível com OpenAI SDK).
"""
import os
from typing import List, Optional
from openai import AsyncOpenAI

from app.config import get_settings


class EmbeddingService:
    """Serviço para gerenciar embeddings vetoriais."""

    def __init__(self):
        settings = get_settings()
        self.client = AsyncOpenAI(
            base_url=settings.openrouter_base_url,
            api_key=settings.openrouter_api_key
        )
        self.model = settings.embedding_model
        self.dimensions = settings.embedding_dimensions

    async def generate_embedding(self, text: str) -> List[float]:
        """
        Gera embedding para um texto.

        Args:
            text: Texto para gerar embedding

        Returns:
            Lista de floats representando o embedding
        """
        # Limpa e trunca texto se necessário
        text = self._prepare_text(text)

        try:
            response = await self.client.embeddings.create(
                model=self.model,
                input=text,
                dimensions=self.dimensions
            )

            return response.data[0].embedding

        except Exception as e:
            # Fallback para modelo padrão se dimensions não suportado
            try:
                response = await self.client.embeddings.create(
                    model="text-embedding-3-small",
                    input=text
                )
                return response.data[0].embedding
            except Exception as fallback_error:
                raise Exception(f"Failed to generate embedding: {str(e)}. Fallback also failed: {str(fallback_error)}")

    async def generate_embeddings_batch(
        self,
        texts: List[str],
        batch_size: int = 100
    ) -> List[List[float]]:
        """
        Gera embeddings para múltiplos textos em batch.

        Args:
            texts: Lista de textos
            batch_size: Tamanho do batch

        Returns:
            Lista de embeddings
        """
        embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch = [self._prepare_text(t) for t in batch]

            try:
                response = await self.client.embeddings.create(
                    model=self.model,
                    input=batch,
                    dimensions=self.dimensions
                )

                batch_embeddings = [item.embedding for item in response.data]
                embeddings.extend(batch_embeddings)

            except Exception as e:
                # Processa individualmente se batch falhar
                for text in batch:
                    embedding = await self.generate_embedding(text)
                    embeddings.append(embedding)

        return embeddings

    def _prepare_text(self, text: str, max_length: int = 8000) -> str:
        """
        Prepara texto para embedding.

        Args:
            text: Texto original
            max_length: Comprimento máximo

        Returns:
            Texto preparado
        """
        if not text:
            return ""

        # Remove caracteres indesejados
        text = text.replace("\n", " ").replace("\r", " ")
        text = " ".join(text.split())

        # Trunca se necessário
        if len(text) > max_length:
            text = text[:max_length]

        return text.strip()

    async def calculate_similarity(
        self,
        embedding1: List[float],
        embedding2: List[float]
    ) -> float:
        """
        Calcula similaridade de cosseno entre dois embeddings.

        Args:
            embedding1: Primeiro embedding
            embedding2: Segundo embedding

        Returns:
            Similaridade entre 0 e 1
        """
        import math

        # Produto escalar
        dot_product = sum(a * b for a, b in zip(embedding1, embedding2))

        # Magnitudes
        magnitude1 = math.sqrt(sum(a * a for a in embedding1))
        magnitude2 = math.sqrt(sum(b * b for b in embedding2))

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        # Similaridade de cosseno
        cosine_similarity = dot_product / (magnitude1 * magnitude2)

        # Normaliza para [0, 1]
        return (cosine_similarity + 1) / 2


# Instância global
embedding_service = EmbeddingService()