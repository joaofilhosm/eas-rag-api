"""
EAS - API RAG Base de Conhecimento
Entry Point Principal
"""
import asyncio
import uvicorn
from app.config import get_settings
from database.database import db


async def startup():
    """Inicialização do banco de dados."""
    print("📡 Conectando ao PostgreSQL...")
    await db.connect()
    print("✓ Conectado ao PostgreSQL")


async def shutdown():
    """Desligamento do banco de dados."""
    print("📡 Desconectando do PostgreSQL...")
    await db.disconnect()
    print("✓ Desconectado do PostgreSQL")


def main():
    """Inicia o servidor da API."""
    settings = get_settings()

    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   EAS - API RAG Base de Conhecimento                        ║
║   Versão: 1.0.0                                              ║
║                                                              ║
║   📡 Servidor: http://{settings.host}:{settings.port}                  ║
║   📚 Docs: http://{settings.host}:{settings.port}/docs               ║
║   🔗 ReDoc: http://{settings.host}:{settings.port}/redoc              ║
║                                                              ║
║   🤖 Modelo: {settings.default_model}                          ║
║   🗄️  Database: PostgreSQL + pgvector                        ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """)

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info" if settings.debug else "warning"
    )


if __name__ == "__main__":
    main()