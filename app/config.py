"""
Configurações da API EAS - Base de Conhecimento RAG
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Configurações da aplicação carregadas de variáveis de ambiente."""

    # Supabase
    supabase_url: str
    supabase_key: str
    supabase_service_key: str

    # OpenRouter (LLM Provider)
    openrouter_api_key: str
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    default_model: str = "openai/gpt-4o-mini"
    fallback_model: str = "anthropic/claude-3.5-sonnet"

    # API Security
    api_master_key: str
    api_key_expiration_days: int = 365

    # Scraper
    scraper_user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    scraper_delay_seconds: float = 2.0
    scraper_max_retries: int = 3

    # Embeddings
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Retorna instância cached das configurações."""
    return Settings()


# Constantes
SCRAPER_SOURCES = {
    "fitness": [
        {
            "name": "Dicas de Treino",
            "url": "https://www.dicasdetreino.com.br",
            "type": "fitness",
            "scrape_frequency_hours": 24
        },
        {
            "name": "Hipertrofia.org",
            "url": "https://www.hipertrofia.org",
            "type": "fitness",
            "scrape_frequency_hours": 24
        }
    ],
    "scientific": [
        {
            "name": "SciELO",
            "url": "https://scielo.org",
            "type": "scientific",
            "scrape_frequency_hours": 168  # 7 dias
        },
        {
            "name": "PubMed",
            "url": "https://pubmed.ncbi.nlm.nih.gov",
            "type": "scientific",
            "scrape_frequency_hours": 168
        },
        {
            "name": "LILACS",
            "url": "https://lilacs.bvsalud.org",
            "type": "scientific",
            "scrape_frequency_hours": 168
        }
    ]
}

SCIENTIFIC_SEARCH_TERMS = [
    "anabolic steroids",
    "androgenic steroids",
    "testosterone replacement therapy",
    "TRT",
    "AAS effects",
    "anabolic androgenic steroids",
    "performance enhancing drugs",
    "PEDs",
    "hormone therapy bodybuilding",
    "esteroides anabolizantes",
    "hormônios esteroides"
]

KNOWLEDGE_CATEGORIES = [
    "treino",
    "nutricao",
    "suplementacao",
    "hormonios",
    "esteroides",
    "medico",
    "cientifico",
    "tecnico",
    "geral"
]