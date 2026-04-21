"""
Serviço de busca ao vivo via scraping.
Quando a base de conhecimento está vazia, faz scraping em tempo real das fontes configuradas.
"""
import asyncio
import aiohttp
from typing import List, Optional, Dict, Any
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from app.config import get_settings
from database.database import db


class LiveSearchService:
    """Serviço para busca ao vivo via scraping de fontes configuradas."""

    def __init__(self):
        settings = get_settings()
        self.scraper_user_agent = settings.scraper_user_agent
        self.scraper_delay = settings.scraper_delay_seconds
        self.timeout = 30
        self.max_pages = 5  # Páginas a buscar no live scrape

    async def search(
        self,
        query: str
    ) -> Dict[str, Any]:
        """
        Busca ao vivo scrapeando fontes configuradas.

        Args:
            query: Pergunta do usuário

        Returns:
            Resultado com conteúdo scrapeado
        """
        # Busca fontes ativas
        sources = await db.get_sources(active_only=True)

        if not sources:
            return {
                "answer": "Nenhuma fonte configurada. Adicione fontes em /api/v1/sources com X-Master-Key.",
                "source": "none",
                "model": None,
                "results": []
            }

        # Filtra fontes relevantes
        relevant_sources = self._filter_relevant_sources(query, sources)

        results = []
        errors = []

        async with aiohttp.ClientSession(
            headers={"User-Agent": self.scraper_user_agent},
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        ) as session:
            for source in relevant_sources[:3]:  # Limite de 3 fontes
                try:
                    scraped = await self._scrape_source(session, source, query)
                    if scraped:
                        results.extend(scraped)
                    await asyncio.sleep(self.scraper_delay)
                except Exception as e:
                    errors.append(f"{source['name']}: {str(e)}")

        if not results:
            return {
                "answer": "Não encontrado nas fontes configuradas. Tente palavras-chave diferentes.",
                "source": "live_scrape",
                "model": None,
                "results": [],
                "errors": errors
            }

        # Formata resposta
        combined = "\n\n---\n\n".join([
            f"**{r['titulo']}**\nFonte: {r['fonte']}\n\n{r['conteudo'][:1500]}"
            for r in results[:3]
        ])

        return {
            "answer": combined,
            "source": "live_scrape",
            "model": None,
            "results": results,
            "errors": errors if errors else None
        }

    def _filter_relevant_sources(self, query: str, sources: List[Dict]) -> List[Dict]:
        """Retorna todas as fontes ativas (sem filtro por tipo)."""
        # Busca em TODAS as fontes, independente do tipo
        return sources

    async def _scrape_source(
        self,
        session: aiohttp.ClientSession,
        source: Dict,
        query: str
    ) -> List[Dict]:
        """Scrapeia uma fonte buscando conteúdo relevante."""
        url = source["url"]
        results = []

        try:
            # 1. Busca página principal
            html = await self._fetch(session, url)
            if not html:
                return []

            soup = BeautifulSoup(html, 'lxml')

            # 2. Descobre links relevantes
            links = self._find_relevant_links(soup, url, query)

            # 3. Scrapeia páginas encontradas
            for link in links[:self.max_pages]:
                page_html = await self._fetch(session, link)
                if page_html:
                    content = self._extract_content(page_html, link)
                    if content:
                        results.append({
                            "titulo": content["titulo"],
                            "conteudo": content["conteudo"],
                            "url": link,
                            "fonte": source["name"],
                            "categoria": content["categoria"]
                        })

        except Exception as e:
            print(f"Erro ao scrapear {url}: {e}")

        return results

    async def _fetch(self, session: aiohttp.ClientSession, url: str) -> Optional[str]:
        """Busca HTML de uma URL."""
        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    return await resp.text()
        except Exception as e:
            print(f"Erro fetch {url}: {e}")
        return None

    def _find_relevant_links(self, soup: BeautifulSoup, base_url: str, query: str) -> List[str]:
        """Encontra links relevantes baseado na query."""
        links = []
        query_words = set(query.lower().split())

        for link in soup.find_all('a', href=True):
            href = link['href']
            full_url = urljoin(base_url, href)

            # Verifica se é do mesmo domínio
            if not self._is_same_domain(base_url, full_url):
                continue

            # Verifica se o link ou texto âncora contém palavras da query
            link_text = link.get_text(strip=True).lower()
            link_href = href.lower()

            # Palavras-chave relevantes
            relevant_keywords = query_words.union({
                'artigo', 'post', 'blog', 'treino', 'exercicio', 'nutricao',
                'suplemento', 'hormonio', 'esteroide', 'ciclo', 'pct'
            })

            if any(kw in link_text or kw in link_href for kw in relevant_keywords):
                links.append(full_url)

        # Remove duplicatas e limita
        return list(dict.fromkeys(links))[:self.max_pages]

    def _extract_content(self, html: str, url: str) -> Optional[Dict]:
        """Extrai conteúdo de uma página."""
        soup = BeautifulSoup(html, 'lxml')

        # Remove ruído
        for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'iframe']):
            tag.decompose()

        # Título
        title = None
        for tag in ['h1', 'title']:
            el = soup.find(tag)
            if el:
                title = el.get_text(strip=True)
                break

        if not title:
            title = url

        # Conteúdo
        content = None
        for sel in ['article', 'main', '.content', '.post-content', '.entry-content', '#content']:
            el = soup.select_one(sel)
            if el:
                content = el.get_text(separator='\n', strip=True)
                break

        if not content:
            content = soup.body.get_text(separator='\n', strip=True) if soup.body else ""

        # Limpa
        content = self._clean_text(content)

        if len(content) < 100:
            return None

        # Categoria
        categoria = self._detect_category(url)

        return {
            "titulo": title[:200],
            "conteudo": content[:5000],
            "categoria": categoria
        }

    def _clean_text(self, text: str) -> str:
        """Limpa texto extraído."""
        import re
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        lines = [l.strip() for l in text.split('\n') if len(l.strip()) > 15]
        return '\n\n'.join(lines)

    def _detect_category(self, url: str) -> str:
        """Detecta categoria pela URL."""
        url_l = url.lower()
        if any(k in url_l for k in ['treino', 'exercicio']):
            return 'treino'
        elif any(k in url_l for k in ['nutri', 'dieta', 'aliment']):
            return 'nutricao'
        elif any(k in url_l for k in ['suplem']):
            return 'suplementacao'
        elif any(k in url_l for k in ['hormo', 'testosterona']):
            return 'hormonios'
        elif any(k in url_l for k in ['estero', 'anabol', 'ciclo']):
            return 'esteroides'
        return 'geral'

    def _is_same_domain(self, base: str, url: str) -> bool:
        """Verifica se é mesmo domínio."""
        return urlparse(base).netloc == urlparse(url).netloc


# Instância global
live_search_service = LiveSearchService()