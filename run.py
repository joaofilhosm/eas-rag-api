"""
EAS - API RAG Base de Conhecimento
Entry Point Principal
"""
import uvicorn
from app.config import get_settings


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
║   🗄️  Database: {settings.supabase_url.split('//')[1].split('.')[0]}              ║
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