"""
Scraper para Dicas de Treino (dicasdetreino.com.br).
"""
import re
from typing import List, Dict, Any
from bs4 import BeautifulSoup

from scraper.base_scraper import BaseScraper


class DicasDeTreinoScraper(BaseScraper):
    """Scraper para o site Dicas de Treino."""

    @property
    def name(self) -> str:
        return "Dicas de Treino"

    @property
    def base_url(self) -> str:
        return "https://www.dicasdetreino.com.br"

    async def get_start_urls(self) -> List[str]:
        """
        Retorna URLs iniciais para scraping.

        Explora:
        - Página principal
        - Categorias principais
        - Arquivos por mês
        """
        return [
            self.base_url,
            f"{self.base_url}/categoria/treinos",
            f"{self.base_url}/categoria/suplementos",
            f"{self.base_url}/categoria/nutricao",
            f"{self.base_url}/categoria/esteroides",
        ]

    async def get_article_links(self, html: str) -> List[str]:
        """
        Extrai links de artigos do Dicas de Treino.

        Args:
            html: HTML da página

        Returns:
            Lista de URLs de artigos
        """
        soup = BeautifulSoup(html, "lxml")
        links = []

        # Seletores comuns para artigos em blogs WordPress
        selectors = [
            "article a",
            ".post-title a",
            ".entry-title a",
            "h2 a",
            "h3 a",
            ".post-content a",
            ".article-link",
            "a[href*='/20']",  # Links com ano
        ]

        for selector in selectors:
            for link in soup.select(selector):
                href = link.get("href", "")
                if href and self.is_valid_url(href):
                    url = self.normalize_url(href)
                    if url not in self.visited_urls:
                        links.append(url)

        # Remove duplicatas e limita
        return list(set(links))[:50]

    def extract_category_from_url(self, url: str) -> str:
        """
        Extrai categoria da URL.

        Args:
            url: URL do artigo

        Returns:
            Categoria detectada
        """
        category_map = {
            "treinos": "treino",
            "treino": "treino",
            "suplementos": "suplementacao",
            "suplementacao": "suplementacao",
            "nutricao": "nutricao",
            "nutrição": "nutricao",
            "esteroides": "esteroides",
            "anabolizantes": "esteroides",
            "hormonios": "hormonios",
        }

        url_lower = url.lower()

        for key, value in category_map.items():
            if key in url_lower:
                return value

        return "geral"

    async def scrape_page(self, url: str) -> Dict[str, Any]:
        """
        Override para adicionar categoria baseada na URL.

        Args:
            url: URL da página

        Returns:
            Conteúdo extraído
        """
        content = await super().scrape_page(url)

        if content:
            # Adiciona categoria se não tiver
            if not content.get("categoria") or content["categoria"] == "geral":
                content["categoria"] = self.extract_category_from_url(url)

        return content