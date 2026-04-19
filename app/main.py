"""
EAS - API RAG Base de Conhecimento
Main FastAPI Application
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
import time
import logging

from app.config import get_settings
from app.routers import (
    health_router,
    api_keys_router,
    search_router,
    knowledge_router,
    scraper_router
)

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerenciamento do ciclo de vida da aplicação."""
    logger.info("🚀 Iniciando EAS API...")
    logger.info(f"📡 Servidor: {settings.host}:{settings.port}")
    logger.info(f"🤖 Modelo padrão: {settings.default_model}")

    # Conecta ao banco de dados PostgreSQL
    from database.database import db
    try:
        await db.connect()
        logger.info("✓ Conectado ao PostgreSQL")
    except Exception as e:
        logger.error(f"✗ Erro ao conectar ao PostgreSQL: {e}")
        raise

    # Inicialização do scheduler de scraping
    # TODO: Implementar scheduler
    # from scraper.scheduler import ScraperScheduler
    # scheduler = ScraperScheduler()
    # scheduler.start()

    yield

    # Cleanup
    logger.info("🛑 Encerrando EAS API...")
    await db.disconnect()
    logger.info("✓ Conexão com PostgreSQL fechada")


# Criação da aplicação FastAPI
app = FastAPI(
    title="EAS - API RAG Base de Conhecimento",
    description="""
    API para base de conhecimento RAG (Retrieval Augmented Generation).

    ## Funcionalidades

    * **Busca Semântica**: Busca inteligente usando embeddings vetoriais
    * **Base de Conhecimento**: Gerenciamento de conhecimento estruturado
    * **Scraper Inteligente**: Coleta automática de dados com IA
    * **API Keys**: Gerenciamento de chaves de acesso

    ## Fontes de Dados

    * Sites de Fitness/Hipertrofia
    * Bases Científicas (SciELO, PubMed, LILACS)
    * Conteúdo customizado

    ## Autenticação

    Use o header `X-API-Key` com sua chave de acesso.
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Middleware de timing
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Adiciona header com tempo de processamento."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = f"{process_time:.4f}"
    return response


# Middleware de logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log de requisições."""
    logger.info(f"📥 {request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"📤 {request.method} {request.url.path} - Status: {response.status_code}")
    return response


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handler global de exceções."""
    logger.error(f"❌ Erro não tratado: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred",
            "detail": str(exc) if settings.debug else None
        }
    )


# Inclusão dos routers
app.include_router(health_router, prefix="/api/v1", tags=["Health"])
app.include_router(api_keys_router, prefix="/api/v1", tags=["API Keys"])
app.include_router(search_router, prefix="/api/v1", tags=["Search"])
app.include_router(knowledge_router, prefix="/api/v1", tags=["Knowledge"])
app.include_router(scraper_router, prefix="/api/v1", tags=["Scraper"])


# Root endpoint
@app.get("/", include_in_schema=False)
async def root():
    """Redirect para documentação."""
    return {
        "name": "EAS - API RAG Base de Conhecimento",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )