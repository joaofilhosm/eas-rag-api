"""
Orquestrador de IA para o Scraper.
Já implementado em app/services/scraper_orchestrator.py
Este arquivo é um wrapper para manter compatibilidade.
"""
from app.services.scraper_orchestrator import ScraperOrchestrator, scraper_orchestrator

__all__ = ["ScraperOrchestrator", "scraper_orchestrator"]