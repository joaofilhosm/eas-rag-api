"""Modelos Pydantic da API EAS."""
from .knowledge import KnowledgeBase, KnowledgeCreate, KnowledgeUpdate, KnowledgeSearch
from .api_key import APIKey, APIKeyCreate, APIKeyResponse
from .scraper import ScraperStatus, ScraperResult, SourceConfig

__all__ = [
    "KnowledgeBase",
    "KnowledgeCreate",
    "KnowledgeUpdate",
    "KnowledgeSearch",
    "APIKey",
    "APIKeyCreate",
    "APIKeyResponse",
    "ScraperStatus",
    "ScraperResult",
    "SourceConfig"
]