"""
Classe base para todos os scrapers.
"""
import asyncio
import re
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from app.config import get_settings
from app.services.scraper_orchestrator import scraper_orchestrator
from database import db


class BaseScraper(ABC):
    """
    Classe base abstrata para scrapers.
    Implementa funcionalidades comuns e define interface.
    """

    def __init__(self, source_config: Dict[str, Any]):
        """
        Inicializa o scraper.

        Args:
            source_config: Configuração da fonte de dados
        """
        self.config = source_config
        self.settings = get_settings()
        self.client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={
                "User-Agent": self.settings.scraper_user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
            }
        )
        self.orchestrator = scraper_orchestrator
        self.visited_urls = set()
        self.results = []

    @property
    @abstractmethod
    def name(self) -> str:
        """Nome do scraper."""
        pass

    @property
    @abstractmethod
    def base_url(self) -> str:
        """URL base do site."""
        pass

    @property
    def source_type(self) -> str:
        """Tipo da fonte (fitness, scientific, etc)."""
        return self.config.get("type", "general")

    @property
    def delay_seconds(self) -> float:
        """Delay entre requisições em segundos."""
        return self.settings.scraper_delay_seconds

    @property
    def max_retries(self) -> int:
        """Número máximo de tentativas."""
        return self.settings.scraper_max_retries

    async def fetch(self, url: str) -> Optional[str]:
        """
        Faz requisição HTTP para uma URL.

        Args:
            url: URL para buscar

        Returns:
            HTML da página ou None se erro
        """
        for attempt in range(self.max_retries):
            try:
                response = await self.client.get(url)
                response.raise_for_status()
                return response.text

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    return None
                if attempt == self.max_retries - 1:
                    raise

            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise

            await asyncio.sleep(self.delay_seconds * (attempt + 1))

        return None

    def normalize_url(self, url: str) -> str:
        """
        Normaliza uma URL relativa para absoluta.

        Args:
            url: URL para normalizar

        Returns:
            URL absoluta
        """
        if url.startswith("http"):
            return url
        return urljoin(self.base_url, url)

    def is_valid_url(self, url: str) -> bool:
        """
        Verifica se uma URL é válida para scraping.

        Args:
            url: URL para verificar

        Returns:
            True se válida
        """
        parsed = urlparse(url)

        # Verifica se é do mesmo domínio
        if parsed.netloc != urlparse(self.base_url).netloc:
            return False

        # Ignora arquivos estáticos
        ignore_extensions = [".jpg", ".jpeg", ".png", ".gif", ".pdf", ".zip", ".mp3", ".mp4"]
        if any(url.lower().endswith(ext) for ext in ignore_extensions):
            return False

        # Ignora URLs de admin, login, etc
        ignore_patterns = ["/admin", "/login", "/logout", "/register", "/search", "/tag/"]
        if any(pattern in url.lower() for pattern in ignore_patterns):
            return False

        return True

    def extract_links(self, html: str, base_url: str) -> List[str]:
        """
        Extrai todos os links de uma página.

        Args:
            html: HTML da página
            base_url: URL base

        Returns:
            Lista de URLs encontradas
        """
        soup = BeautifulSoup(html, "lxml")
        links = []

        for link in soup.find_all("a", href=True):
            href = link["href"]
            url = self.normalize_url(href)

            if self.is_valid_url(url) and url not in self.visited_urls:
                links.append(url)

        return list(set(links))

    async def scrape_page(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Faz scraping de uma página e extrai conteúdo com IA.

        Args:
            url: URL da página

        Returns:
            Dicionário com conteúdo extraído
        """
        if url in self.visited_urls:
            return None

        self.visited_urls.add(url)
        html = await self.fetch(url)

        if not html:
            return None

        # Usa IA para extrair conteúdo
        if self.source_type == "scientific":
            content = await self.orchestrator.extract_scientific_content(html, url)
        else:
            content = await self.orchestrator.extract_content(html, url, self.source_type)

        if content:
            content["url_original"] = url
            content["source_id"] = self.config.get("id")

        return content

    async def save_content(self, content: Dict[str, Any]) -> bool:
        """
        Salva conteúdo extraído no banco de dados.

        Args:
            content: Conteúdo extraído

        Returns:
            True se salvo com sucesso
        """
        try:
            result = await db.create_knowledge(
                titulo=content.get("titulo", "Sem título"),
                conteudo=content.get("conteudo", ""),
                source_id=content.get("source_id"),
                categoria=content.get("categoria"),
                tags=content.get("tags", []),
                url_original=content.get("url_original"),
                metadata=content.get("metadata", {})
            )
            return result is not None

        except Exception as e:
            print(f"Erro ao salvar conteúdo: {e}")
            return False

    @abstractmethod
    async def get_start_urls(self) -> List[str]:
        """
        Retorna URLs iniciais para começar o scraping.

        Returns:
            Lista de URLs iniciais
        """
        pass

    @abstractmethod
    async def get_article_links(self, html: str) -> List[str]:
        """
        Extrai links de artigos de uma página.

        Args:
            html: HTML da página

        Returns:
            Lista de URLs de artigos
        """
        pass

    async def scrape(self, max_pages: int = 100) -> Dict[str, Any]:
        """
        Executa o scraping completo.

        Args:
            max_pages: Número máximo de páginas

        Returns:
            Estatísticas do scraping
        """
        start_time = datetime.utcnow()
        items_extracted = 0
        items_failed = 0
        errors = []

        try:
            # Pega URLs iniciais
            start_urls = await self.get_start_urls()

            for start_url in start_urls:
                if items_extracted >= max_pages:
                    break

                # Busca página inicial
                html = await self.fetch(start_url)

                if not html:
                    errors.append(f"Failed to fetch {start_url}")
                    continue

                # Extrai links de artigos
                article_links = await self.get_article_links(html)

                for link in article_links:
                    if items_extracted >= max_pages:
                        break

                    await asyncio.sleep(self.delay_seconds)

                    content = await self.scrape_page(link)

                    if content:
                        saved = await self.save_content(content)

                        if saved:
                            items_extracted += 1
                            self.results.append(content)
                        else:
                            items_failed += 1
                    else:
                        items_failed += 1

        except Exception as e:
            errors.append(str(e))

        end_time = datetime.utcnow()

        # Atualiza log de scraping
        await db.create_scrape_log(
            source_id=self.config.get("id"),
            status="success" if items_extracted > 0 else "error",
            items_extracted=items_extracted,
            items_failed=items_failed,
            error_message="\n".join(errors) if errors else None,
            started_at=start_time.isoformat(),
            completed_at=end_time.isoformat(),
            duration_seconds=(end_time - start_time).total_seconds()
        )

        # Atualiza última execução da fonte
        if self.config.get("id"):
            await db.update_source_last_scraped(self.config["id"])

        return {
            "source": self.name,
            "items_extracted": items_extracted,
            "items_failed": items_failed,
            "duration_seconds": (end_time - start_time).total_seconds(),
            "errors": errors
        }

    async def close(self):
        """Fecha o cliente HTTP."""
        await self.client.aclose()