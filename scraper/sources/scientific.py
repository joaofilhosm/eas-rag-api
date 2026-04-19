"""
Scraper para bases científicas (SciELO, PubMed, LILACS).
"""
import re
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from urllib.parse import quote_plus

from scraper.base_scraper import BaseScraper
from app.config import SCIENTIFIC_SEARCH_TERMS


class ScientificScraper(BaseScraper):
    """Scraper para bases de dados científicas."""

    # Configurações por base de dados
    DATABASES = {
        "scielo": {
            "name": "SciELO",
            "base_url": "https://scielo.org",
            "search_url": "https://search.scielo.org/?q={query}&lang=pt",
            "article_selector": ".result-item a[href*='article']",
        },
        "pubmed": {
            "name": "PubMed",
            "base_url": "https://pubmed.ncbi.nlm.nih.gov",
            "search_url": "https://pubmed.ncbi.nlm.nih.gov/?term={query}",
            "article_selector": ".docsum-title",
        },
        "lilacs": {
            "name": "LILACS",
            "base_url": "https://lilacs.bvsalud.org",
            "search_url": "https://lilacs.bvsalud.org/global-search/?q={query}",
            "article_selector": ".record-title a",
        },
    }

    def __init__(self, source_config: Dict[str, Any]):
        """
        Inicializa o scraper científico.

        Args:
            source_config: Configuração da fonte (deve incluir 'database' key)
        """
        super().__init__(source_config)
        self.database_key = source_config.get("database", "scielo")
        self.database = self.DATABASES.get(self.database_key, self.DATABASES["scielo"])
        self.search_terms = source_config.get("search_terms", SCIENTIFIC_SEARCH_TERMS)

    @property
    def name(self) -> str:
        return self.database["name"]

    @property
    def base_url(self) -> str:
        return self.database["base_url"]

    @property
    def source_type(self) -> str:
        return "scientific"

    async def get_start_urls(self) -> List[str]:
        """
        Gera URLs de busca para cada termo.

        Returns:
            Lista de URLs de busca
        """
        urls = []

        # Limita termos para não sobrecarregar
        terms = self.search_terms[:5] if len(self.search_terms) > 5 else self.search_terms

        for term in terms:
            encoded_term = quote_plus(term)
            url = self.database["search_url"].format(query=encoded_term)
            urls.append(url)

        return urls

    async def get_article_links(self, html: str) -> List[str]:
        """
        Extrai links de artigos científicos.

        Args:
            html: HTML da página de resultados

        Returns:
            Lista de URLs de artigos
        """
        soup = BeautifulSoup(html, "lxml")
        links = []

        # Seletores específicos para artigos
        selectors = [
            self.database.get("article_selector", ".result-item a"),
            "a[href*='article']",
            "a[href*='abstract']",
            "a[href*='full']",
            ".title a",
            ".article-title a",
        ]

        for selector in selectors:
            for link in soup.select(selector):
                href = link.get("href", "")

                if href:
                    url = self.normalize_url(href)

                    # Filtra links não relevantes
                    if any(x in url.lower() for x in ["pdf", "download", "supplement"]):
                        continue

                    if url not in self.visited_urls:
                        links.append(url)

        # Remove duplicatas
        return list(set(links))[:30]

    async def extract_abstract(self, html: str, url: str) -> Optional[Dict[str, Any]]:
        """
        Extrai abstract de artigo científico.

        Args:
            html: HTML do artigo
            url: URL do artigo

        Returns:
            Dicionário com dados do artigo
        """
        soup = BeautifulSoup(html, "lxml")

        # Tenta extrair título
        title = None
        for selector in ["h1", ".article-title", ".title", "meta[name='citation_title']"]:
            element = soup.select_one(selector)
            if element:
                if element.name == "meta":
                    title = element.get("content", "")
                else:
                    title = element.get_text(strip=True)
                break

        if not title:
            title = "Sem título"

        # Tenta extrair abstract
        abstract = None
        for selector in [".abstract", ".abstract-content", "#abstract", "meta[name='citation_abstract']"]:
            element = soup.select_one(selector)
            if element:
                if element.name == "meta":
                    abstract = element.get("content", "")
                else:
                    abstract = element.get_text(strip=True)
                break

        if not abstract:
            # Fallback: primeiro parágrafo significativo
            for p in soup.find_all("p"):
                text = p.get_text(strip=True)
                if len(text) > 100:  # Pelo menos 100 caracteres
                    abstract = text[:2000]  # Limita a 2000 chars
                    break

        if not abstract:
            return None

        # Tenta extrair autores
        authors = []
        for selector in [".authors", ".author", "meta[name='citation_author']"]:
            elements = soup.select(selector)
            for element in elements:
                if element.name == "meta":
                    authors.append(element.get("content", ""))
                else:
                    authors.append(element.get_text(strip=True))

        # Tenta extrair ano
        year = None
        for selector in ["meta[name='citation_year']", "meta[name='citation_publication_date']"]:
            element = soup.select_one(selector)
            if element:
                date_str = element.get("content", "")
                year_match = re.search(r"\d{4}", date_str)
                if year_match:
                    year = year_match.group()

        # Tenta extrair DOI
        doi = None
        for selector in ["meta[name='citation_doi']", "a[href*='doi.org']"]:
            element = soup.select_one(selector)
            if element:
                if element.name == "meta":
                    doi = element.get("content", "")
                else:
                    href = element.get("href", "")
                    doi_match = re.search(r"10\.\d{4,}/[^\s]+", href)
                    if doi_match:
                        doi = doi_match.group()

        return {
            "titulo": title[:500],
            "conteudo": abstract,
            "categoria": "cientifico",
            "tags": self._extract_keywords(abstract),
            "metadata": {
                "autores": authors[:5],  # Máximo 5 autores
                "ano": year,
                "doi": doi,
                "fonte": self.database["name"],
            },
            "url_original": url,
        }

    def _extract_keywords(self, text: str) -> List[str]:
        """
        Extrai palavras-chave do texto.

        Args:
            text: Texto para extrair

        Returns:
            Lista de palavras-chave
        """
        # Termos relevantes para fitness/esteroides
        keywords = []

        relevant_terms = [
            "testosterone", "testosterona", "anabolic", "anabólico",
            "steroid", "esteroide", "hormone", "hormônio",
            "muscle", "músculo", "hypertrophy", "hipertrofia",
            "strength", "força", "exercise", "exercício",
            "training", "treino", "performance", "desempenho",
            "supplement", "suplemento", "nutrition", "nutrição",
            "doping", "wada", "adverse", "efeitos colaterais",
            "cardiovascular", "hepatic", "hepático",
            "androgen", "androgênio", "estrogen", "estrogênio",
        ]

        text_lower = text.lower()

        for term in relevant_terms:
            if term in text_lower and term not in keywords:
                keywords.append(term)

        return keywords[:10]  # Máximo 10

    async def scrape_page(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Override para usar extração específica de artigos científicos.

        Args:
            url: URL do artigo

        Returns:
            Conteúdo extraído
        """
        if url in self.visited_urls:
            return None

        self.visited_urls.add(url)
        html = await self.fetch(url)

        if not html:
            return None

        # Tenta extração específica primeiro
        content = await self.extract_abstract(html, url)

        if not content:
            # Fallback para extração com IA
            content = await self.orchestrator.extract_scientific_content(html, url)

        if content:
            content["url_original"] = url
            content["source_id"] = self.config.get("id")

        return content