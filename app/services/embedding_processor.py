"""
Script para processar embeddings em lote.
"""
import asyncio
from typing import List, Dict, Any

from app.services.embeddings import embedding_service
from database.database import db


class EmbeddingProcessor:
    """Processador de embeddings para conhecimentos pendentes."""

    def __init__(self, batch_size: int = 10):
        """
        Inicializa o processador.

        Args:
            batch_size: Tamanho do batch para processamento
        """
        self.batch_size = batch_size
        self.embedding_service = embedding_service

    async def get_pending_knowledge(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Busca conhecimentos sem embedding.

        Args:
            limit: Número máximo de registros

        Returns:
            Lista de conhecimentos pendentes
        """
        results = await db.fetch(
            "SELECT * FROM knowledge_base WHERE embedding_status = 'pending' LIMIT $1",
            limit
        )
        return [dict(r) for r in results]

    async def process_batch(self) -> Dict[str, int]:
        """
        Processa um batch de conhecimentos.

        Returns:
            Estatísticas do processamento
        """
        # Busca pendentes
        pending = await self.get_pending_knowledge(limit=self.batch_size)

        if not pending:
            return {"processed": 0, "failed": 0, "total": 0}

        processed = 0
        failed = 0

        for knowledge in pending:
            try:
                # Gera embedding
                text = f"{knowledge['titulo']}\n\n{knowledge['conteudo']}"
                embedding = await self.embedding_service.generate_embedding(text)

                # Salva embedding
                await db.create_embedding(
                    knowledge_id=knowledge["id"],
                    embedding=embedding
                )

                processed += 1
                print(f"✓ Embedding processado: {knowledge['titulo'][:50]}...")

            except Exception as e:
                failed += 1
                print(f"✗ Erro ao processar {knowledge['id']}: {str(e)}")

                # Marca como erro
                await db.execute(
                    "UPDATE knowledge_base SET embedding_status = 'error' WHERE id = $1",
                    knowledge["id"]
                )

        return {
            "processed": processed,
            "failed": failed,
            "total": len(pending)
        }

    async def process_all(self) -> Dict[str, int]:
        """
        Processa todos os conhecimentos pendentes.

        Returns:
            Estatísticas totais
        """
        total_processed = 0
        total_failed = 0
        total_batches = 0

        while True:
            result = await self.process_batch()

            total_processed += result["processed"]
            total_failed += result["failed"]
            total_batches += 1

            # Para se não houver mais pendentes
            if result["total"] == 0:
                break

            # Pausa entre batches
            await asyncio.sleep(1)

        return {
            "processed": total_processed,
            "failed": total_failed,
            "batches": total_batches
        }

    async def process_knowledge(self, knowledge_id: str) -> bool:
        """
        Processa embedding para um conhecimento específico.

        Args:
            knowledge_id: ID do conhecimento

        Returns:
            True se processado com sucesso
        """
        try:
            # Busca conhecimento
            knowledge = await db.get_knowledge(knowledge_id)

            if not knowledge:
                return False

            # Gera embedding
            text = f"{knowledge['titulo']}\n\n{knowledge['conteudo']}"
            embedding = await self.embedding_service.generate_embedding(text)

            # Salva embedding
            await db.create_embedding(
                knowledge_id=knowledge["id"],
                embedding=embedding
            )

            return True

        except Exception as e:
            print(f"Erro ao processar conhecimento {knowledge_id}: {str(e)}")
            return False


async def main():
    """Função principal para execução standalone."""
    # Conecta ao banco
    await db.connect()

    try:
        processor = EmbeddingProcessor(batch_size=10)

        print("Iniciando processamento de embeddings...")
        result = await processor.process_all()

        print(f"\nProcessamento concluído:")
        print(f"  - Processados: {result['processed']}")
        print(f"  - Falhas: {result['failed']}")
        print(f"  - Batches: {result['batches']}")
    finally:
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(main())