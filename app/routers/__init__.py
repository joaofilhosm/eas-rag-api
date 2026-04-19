"""Routers da API EAS."""
from .health import router as health_router
from .api_keys import router as api_keys_router
from .search import router as search_router
from .knowledge import router as knowledge_router
from .scraper import router as scraper_router

__all__ = [
    "health_router",
    "api_keys_router",
    "search_router",
    "knowledge_router",
    "scraper_router"
]