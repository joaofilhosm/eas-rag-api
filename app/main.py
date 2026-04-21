"""
EAS - API RAG Base de Conhecimento
Main FastAPI Application
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.encoders import jsonable_encoder
import time
import logging
import os

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
        "redoc": "/redoc",
        "lovable": "/lovable"
    }


# Lovable documentation endpoint
@app.get("/lovable", response_class=HTMLResponse, include_in_schema=False)
async def lovable_docs():
    """Serve Lovable integration documentation as HTML."""
    docs_path = os.path.join(os.path.dirname(__file__), "..", "docs", "lovable_prompt.md")

    try:
        with open(docs_path, "r", encoding="utf-8") as f:
            md_content = f.read()
    except FileNotFoundError:
        return HTMLResponse(
            content="<h1>Documentação não encontrada</h1><p>Arquivo docs/lovable_prompt.md não existe.</p>",
            status_code=404
        )

    # Convert markdown to HTML (simple conversion)
    html_content = f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EAS API - Prompt para Lovable</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            line-height: 1.6;
            color: #e0e0e0;
            background: #1a1a2e;
            padding: 20px;
            max-width: 900px;
            margin: 0 auto;
        }}
        h1 {{
            color: #00d9ff;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #00d9ff;
        }}
        h2 {{
            color: #ff6b6b;
            margin: 30px 0 15px;
        }}
        h3 {{
            color: #ffd93d;
            margin: 20px 0 10px;
        }}
        h4 {{
            color: #6bcb77;
            margin: 15px 0 10px;
        }}
        p {{
            margin: 10px 0;
        }}
        code {{
            background: #16213e;
            padding: 2px 6px;
            border-radius: 4px;
            font-family: 'Fira Code', 'Consolas', monospace;
            font-size: 0.9em;
            color: #00d9ff;
        }}
        pre {{
            background: #16213e;
            padding: 15px;
            border-radius: 8px;
            overflow-x: auto;
            margin: 15px 0;
            border-left: 4px solid #00d9ff;
        }}
        pre code {{
            background: none;
            padding: 0;
            color: #e0e0e0;
        }}
        blockquote {{
            border-left: 4px solid #ffd93d;
            margin: 15px 0;
            padding: 10px 20px;
            background: rgba(255, 217, 61, 0.1);
        }}
        ul, ol {{
            margin: 10px 0 10px 25px;
        }}
        li {{
            margin: 5px 0;
        }}
        a {{
            color: #00d9ff;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
        hr {{
            border: none;
            border-top: 1px solid #333;
            margin: 30px 0;
        }}
        strong {{
            color: #ff6b6b;
        }}
        .header {{
            text-align: center;
            padding: 30px 0;
            margin-bottom: 30px;
        }}
        .header h1 {{
            border: none;
            margin-bottom: 10px;
        }}
        .subtitle {{
            color: #888;
            font-size: 1.1em;
        }}
        .nav {{
            display: flex;
            gap: 15px;
            justify-content: center;
            margin: 20px 0;
        }}
        .nav a {{
            padding: 8px 16px;
            background: #16213e;
            border-radius: 6px;
            border: 1px solid #333;
        }}
        .nav a:hover {{
            background: #1a1a2e;
            border-color: #00d9ff;
        }}
        .copy-btn {{
            position: absolute;
            top: 8px;
            right: 8px;
            padding: 5px 10px;
            background: #00d9ff;
            color: #1a1a2e;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
        }}
        .copy-btn:hover {{
            background: #00b8d9;
        }}
        .code-block {{
            position: relative;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🤖 EAS API RAG</h1>
        <p class="subtitle">Prompt para Integração com Lovable / ChatGPT</p>
        <div class="nav">
            <a href="/">← Voltar</a>
            <a href="/docs">📚 Swagger Docs</a>
            <a href="/redoc">📖 ReDoc</a>
        </div>
    </div>
    <hr>
    {markdown_to_html(md_content)}
</body>
</html>
"""
    return HTMLResponse(content=html_content)


def markdown_to_html(md: str) -> str:
    """Simple markdown to HTML converter."""
    import re

    # Escape HTML
    md = md.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # Headers
    md = re.sub(r'^# (.+)$', r'<h1>\1</h1>', md, flags=re.MULTILINE)
    md = re.sub(r'^## (.+)$', r'<h2>\1</h2>', md, flags=re.MULTILINE)
    md = re.sub(r'^### (.+)$', r'<h3>\1</h3>', md, flags=re.MULTILINE)
    md = re.sub(r'^#### (.+)$', r'<h4>\1</h4>', md, flags=re.MULTILINE)

    # Bold
    md = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', md)

    # Italic
    md = re.sub(r'\*(.+?)\*', r'<em>\1</em>', md)

    # Code blocks
    md = re.sub(r'```(\w+)?\n(.*?)```', r'<div class="code-block"><pre><code>\2</code></pre></div>', md, flags=re.DOTALL)

    # Inline code
    md = re.sub(r'`([^`]+)`', r'<code>\1</code>', md)

    # Blockquotes
    md = re.sub(r'^&gt; (.+)$', r'<blockquote>\1</blockquote>', md, flags=re.MULTILINE)

    # Horizontal rules
    md = re.sub(r'^---$', r'<hr>', md, flags=re.MULTILINE)

    # Lists
    md = re.sub(r'^- (.+)$', r'<li>\1</li>', md, flags=re.MULTILINE)
    md = re.sub(r'^(\d+)\. (.+)$', r'<li>\2</li>', md, flags=re.MULTILINE)

    # Wrap consecutive li elements in ul
    md = re.sub(r'(<li>.*?</li>\n)+', r'<ul>\g<0></ul>\n', md)

    # Paragraphs
    md = re.sub(r'\n\n', r'</p><p>', md)
    md = f'<p>{md}</p>'

    # Clean up
    md = re.sub(r'<p><h', r'<h', md)
    md = re.sub(r'</h(\d)></p>', r'</h\1>', md)
    md = re.sub(r'<p><hr></p>', r'<hr>', md)
    md = re.sub(r'<p><ul>', r'<ul>', md)
    md = re.sub(r'</ul></p>', r'</ul>', md)
    md = re.sub(r'<p><blockquote>', r'<blockquote>', md)
    md = re.sub(r'</blockquote></p>', r'</blockquote>', md)
    md = re.sub(r'<p><div', r'<div', md)
    md = re.sub(r'</div></p>', r'</div>', md)

    return md




@app.get("/playground", response_class=HTMLResponse, include_in_schema=False)
async def playground():
    """Interactive API playground."""
    playground_path = os.path.join(os.path.dirname(__file__), "templates", "playground.html")
    try:
        with open(playground_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Playground not found</h1>", status_code=404)




if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )