"""
Scraper para Hipertrofia.org.
"""
import re
from typing import List, Dict, Any
from bs4 import BeautifulSoup

from scraper.base_scraper import BaseScraper


class HipertrofiaOrgScraper(BaseScraper):
    """Scraper para o site Hipertrofia.org."""

    @property
    def name(self) -> str:
        return "Hipertrofia.org"

    @property
    def base_url(self) -> str:
        return "https://www.hipertrofia.org"

    async def get_start_urls(self) -> List[str]:
        """
        Retorna URLs iniciais para scraping.

        Explora:
        - Fórum principal
        - Seções de artigos
        - Categorias populares
        """
        return [
            self.base_url,
            f"{self.base_url}/artigos",
            f"{self.base_url}/forum",
            f"{self.base_url}/blog",
        ]

    async def get_article_links(self, html: str) -> List[str]:
        """
        Extrai links de artigos do Hipertrofia.org.

        Args:
            html: HTML da página

        Returns:
            Lista de URLs de artigos
        """
        soup = BeautifulSoup(html, "lxml")
        links = []

        # Seletores específicos do site
        selectors = [
            ".post-title a",
            ".entry-title a",
            "article a",
            ".topic-title a",
            ".thread-title a",
            "a[href*='/artigo']",
            "a[href*='/blog']",
            ".content-item a",
            "h2 a",
            "h3 a",
        ]

        for selector in selectors:
            for link in soup.select(selector):
                href = link.get("href", "")
                if href and self.is_valid_url(href):
                    url = self.normalize_url(href)

                    # Filtra links de fórum muito específicos
                    if "/member" not in url and "/profile" not in url:
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
            "treino": "treino",
            "treinos": "treino",
            "exercicio": "treino",
            "nutricao": "nutricao",
            "nutrição": "nutricao",
            "dieta": "nutricao",
            "suplemento": "suplementacao",
            "suplementos": "suplementacao",
            "esteroides": "esteroides",
            "anabolizante": "esteroides",
            "hormonio": "hormonios",
            "artigo": "cientifico",
            "estudo": "cientifico",
        }

        url_lower = url.lower()

        for key, value in category_map.items():
            if key in url_lower:
                return value

        return "geral"

    def is_forum_post(self, url: str) -> bool:
        """
        Verifica se é um post de fórum.

        Args:
            url: URL para verificar

        Returns:
            True se for post de fórum
        """
        forum_patterns = ["/forum/", "/thread/", "/topic/", "/post/"]
        return any(pattern in url.lower() for pattern in forum_patterns)

    async def scrape_page(self, url: str) -> Dict[str, Any]:
        """
        Override para tratamento especial de posts de fórum.

        Args:
            url: URL da página

        Returns:
            Conteúdo extraído
        """
        content = await super().scrape_page(url)

        if content:
            # Adiciona categoria
            if not content.get("categoria") or content["categoria"] == "geral":
                content["categoria"] = self.extract_category_from_url(url)

            # Marca se é de fórum
            if self.is_forum_post(url):
                content["metadata"]["source_type"] = "forum"
                content["tags"].append("forum")

        return content