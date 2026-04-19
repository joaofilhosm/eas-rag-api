"""Fontes de dados do Scraper."""
from .dicasdetreino import DicasDeTreinoScraper
from .hipertrofia_org import HipertrofiaOrgScraper
from .scientific import ScientificScraper

__all__ = [
    "DicasDeTreinoScraper",
    "HipertrofiaOrgScraper",
    "ScientificScraper"
]