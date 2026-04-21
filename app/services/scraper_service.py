"""
Serviço de Scraper Contínuo.
Scrapeia todas as fontes configuradas de forma automática e contínua.
"""
import asyncio
import aiohttp
from typing import List, Optional, Dict, Any, Set
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from datetime import datetime
import re

from app.config import get_settings
from database.database import db


class ScraperService:
    """Serviço para scraping contínuo de fontes."""

    def __init__(self):
        settings = get_settings()
        self.scraper_user_agent = settings.scraper_user_agent
        self.scraper_delay = settings.scraper_delay_seconds
        self.scraper_max_retries = settings.scraper_max_retries
        self.timeout = 30
        self.max_pages_per_source = 100  # Limite de páginas por fonte
        self.max_concurrent = 3  # Requisições concorrentes

    async def scrape_source(
        self,
        source: Dict[str, Any],
        session: aiohttp.ClientSession
    ) -> Dict[str, Any]:
        """
        Scrapeia uma fonte completa, extraindo todas as páginas.

        Args:
            source: Dados da fonte
            session: Sessão HTTP

        Returns:
            Resultado do scraping
        """
        source_id = source["id"]
        source_url = source["url"]
        source_name = source["name"]
        source_type = source.get("type", "general")

        result = {
            "source_id": source_id,
            "source_name": source_name,
            "pages_scraped": 0,
            "items_saved": 0,
            "errors": [],
            "urls_found": [],
            "urls_scraped": []
        }

        try:
            # 1. Descobre todas as URLs do site
            urls = await self._discover_urls(session, source_url, source_type)
            result["urls_found"] = urls
            result["total_urls"] = len(urls)

            # 2. Scrapeia cada URL
            for i, url in enumerate(urls[:self.max_pages_per_source]):
                try:
                    content = await self._scrape_page(session, url, source_type)

                    if content:
                        # Salva na base de conhecimento
                        await self._save_to_knowledge(
                            source_id=source_id,
                            url=url,
                            content=content
                        )
                        result["items_saved"] += 1

                    result["urls_scraped"].append(url)
                    result["pages_scraped"] += 1

                    # Delay entre requisições
                    await asyncio.sleep(self.scraper_delay)

                except Exception as e:
                    result["errors"].append(f"{url}: {str(e)}")

            # 3. Atualiza status da fonte
            await db.update_source_last_scraped(source_id)

            result["status"] = "success" if result["items_saved"] > 0 else "error"

        except Exception as e:
            result["status"] = "error"
            result["errors"].append(f"Erro geral: {str(e)}")

        return result

    async def _discover_urls(
        self,
        session: aiohttp.ClientSession,
        base_url: str,
        source_type: str
    ) -> List[str]:
        """
        Descobre todas as URLs de um site.

        Args:
            session: Sessão HTTP
            base_url: URL base
            source_type: Tipo da fonte

        Returns:
            Lista de URLs encontradas
        """
        urls: Set[str] = set()
        visited: Set[str] = set()

        # URLs iniciais
        urls.add(base_url)

        # Padrões de URLs para buscar
        patterns = self._get_url_patterns(base_url, source_type)

        # Busca página inicial
        try:
            html = await self._fetch_page(session, base_url)
            if html:
                soup = BeautifulSoup(html, 'lxml')

                # Extrai todos os links
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    full_url = urljoin(base_url, href)

                    # Filtra URLs do mesmo domínio
                    if self._is_same_domain(base_url, full_url):
                        # Normaliza URL
                        clean_url = self._normalize_url(full_url)
                        if clean_url and clean_url not in visited:
                            urls.add(clean_url)

                # Busca padrões específicos
                for pattern in patterns:
                    if pattern not in visited:
                        urls.add(pattern)

        except Exception as e:
            print(f"Erro ao descobrir URLs de {base_url}: {e}")

        # Limita número de URLs
        return list(urls)[:self.max_pages_per_source]

    def _get_url_patterns(self, base_url: str, source_type: str) -> List[str]:
        """Retorna padrões de URLs baseado no tipo de fonte."""
        parsed = urlparse(base_url)
        base = f"{parsed.scheme}://{parsed.netloc}"

        patterns = []

        if source_type == "fitness":
            patterns.extend([
                f"{base}/artigos/",
                f"{base}/posts/",
                f"{base}/blog/",
                f"{base}/treinos/",
                f"{base}/exercicios/",
                f"{base}/nutricao/",
                f"{base}/suplementos/",
            ])
        elif source_type == "scientific":
            patterns.extend([
                f"{base}/articles/",
                f"{base}/search/",
                f"{base}/results/",
            ])

        return patterns

    async def _fetch_page(
        self,
        session: aiohttp.ClientSession,
        url: str
    ) -> Optional[str]:
        """Busca o HTML de uma página."""
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.text()
        except Exception as e:
            print(f"Erro ao buscar {url}: {e}")
        return None

    async def _scrape_page(
        self,
        session: aiohttp.ClientSession,
        url: str,
        source_type: str
    ) -> Optional[Dict[str, Any]]:
        """
        Scrapeia uma página específica.

        Args:
            session: Sessão HTTP
            url: URL da página
            source_type: Tipo da fonte

        Returns:
            Conteúdo extraído ou None
        """
        html = await self._fetch_page(session, url)
        if not html:
            return None

        soup = BeautifulSoup(html, 'lxml')

        # Remove elementos não relevantes
        for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'iframe', 'form', 'button']):
            tag.decompose()

        # Extrai título
        title = None
        for tag in ['h1', 'title']:
            element = soup.find(tag)
            if element:
                title = element.get_text(strip=True)
                break

        if not title:
            title = url

        # Extrai conteúdo principal
        content = None
        for selector in ['article', 'main', '.content', '.post-content', '.entry-content', '.article-content', '#content', '.post', '.article']:
            element = soup.select_one(selector)
            if element:
                content = element.get_text(separator='\n', strip=True)
                break

        if not content:
            content = soup.body.get_text(separator='\n', strip=True) if soup.body else ""

        # Limpa e processa conteúdo
        content = self._clean_content(content)

        # Limita tamanho
        if len(content) > 10000:
            content = content[:10000]

        # Extrai categoria
        categoria = self._extract_category(url, source_type)

        # Extrai tags
        tags = self._extract_tags(soup)

        return {
            "titulo": title[:500] if title else "Sem título",
            "conteudo": content,
            "categoria": categoria,
            "tags": tags,
            "url_original": url
        }

    def _clean_content(self, content: str) -> str:
        """Limpa o conteúdo extraído."""
        # Remove múltiplos espaços
        content = re.sub(r'\s+', ' ', content)

        # Remove múltiplas quebras de linha
        content = re.sub(r'\n{3,}', '\n\n', content)

        # Remove linhas muito curtas (prováveis ruídos)
        lines = content.split('\n')
        lines = [l.strip() for l in lines if len(l.strip()) > 10]

        return '\n\n'.join(lines)

    def _extract_category(self, url: str, source_type: str) -> str:
        """Extrai categoria baseado na URL e tipo."""
        url_lower = url.lower()

        if any(kw in url_lower for kw in ['treino', 'treinos', 'exercicios', 'workout']):
            return 'treino'
        elif any(kw in url_lower for kw in ['nutricao', 'dieta', 'alimentacao', 'comida']):
            return 'nutricao'
        elif any(kw in url_lower for kw in ['suplemento', 'suplementacao', 'whey', 'creatina']):
            return 'suplementacao'
        elif any(kw in url_lower for kw in ['hormonio', 'testosterona', 'gh']):
            return 'hormonios'
        elif any(kw in url_lower for kw in ['esteroide', 'anabolizante', 'ciclo', 'pct']):
            return 'esteroides'
        elif any(kw in url_lower for kw in ['medico', 'saude', 'clinica']):
            return 'medico'
        elif source_type == 'scientific':
            return 'cientifico'
        else:
            return 'geral'

    def _extract_tags(self, soup: BeautifulSoup) -> List[str]:
        """Extrai tags do HTML."""
        tags = []

        # Meta keywords
        meta = soup.find('meta', attrs={'name': 'keywords'})
        if meta and meta.get('content'):
            tags.extend([t.strip() for t in meta['content'].split(',')])

        # Tags em elementos específicos
        for tag_elem in soup.find_all(['tag', 'a'], class_=lambda x: x and ('tag' in x.lower() if x else False)):
            tag_text = tag_elem.get_text(strip=True)
            if tag_text and len(tag_text) < 50:
                tags.append(tag_text)

        # Remove duplicatas e limita
        tags = list(set(tags))[:10]

        return tags

    def _is_same_domain(self, base_url: str, url: str) -> bool:
        """Verifica se a URL é do mesmo domínio."""
        base_domain = urlparse(base_url).netloc
        url_domain = urlparse(url).netloc
        return base_domain == url_domain

    def _normalize_url(self, url: str) -> Optional[str]:
        """Normaliza uma URL."""
        try:
            parsed = urlparse(url)

            # Ignora URLs com âncora
            if '#' in url:
                url = url.split('#')[0]

            # Ignora URLs com query complexa
            if len(parsed.query) > 100:
                return None

            # Ignora extensões não relevantes
            ignore_extensions = ['.pdf', '.jpg', '.png', '.gif', '.zip', '.mp4', '.mp3']
            if any(url.lower().endswith(ext) for ext in ignore_extensions):
                return None

            return url
        except:
            return None

    async def _save_to_knowledge(
        self,
        source_id: str,
        url: str,
        content: Dict[str, Any]
    ) -> None:
        """Salva conteúdo na base de conhecimento."""
        try:
            # Cria registro na base
            knowledge = await db.create_knowledge(
                titulo=content["titulo"],
                conteudo=content["conteudo"],
                source_id=source_id,
                categoria=content["categoria"],
                tags=content["tags"],
                url_original=url
            )

            # TODO: Gerar embedding quando implementar
            # embedding = await embedding_service.generate_embedding(content["conteudo"])
            # await db.create_embedding(knowledge["id"], embedding)

        except Exception as e:
            print(f"Erro ao salvar conhecimento: {e}")
            raise

    async def scrape_all_sources(self) -> Dict[str, Any]:
        """
        Scrapeia todas as fontes ativas.

        Returns:
            Resultado geral do scraping
        """
        sources = await db.get_sources(active_only=True)

        if not sources:
            return {
                "status": "no_sources",
                "message": "Nenhuma fonte ativa configurada"
            }

        results = []
        total_items = 0
        total_errors = []

        async with aiohttp.ClientSession(
            headers={"User-Agent": self.scraper_user_agent},
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        ) as session:
            for source in sources:
                # Verifica se precisa fazer scraping
                if not self._should_scrape(source):
                    continue

                result = await self.scrape_source(source, session)
                results.append(result)
                total_items += result.get("items_saved", 0)
                total_errors.extend(result.get("errors", []))

        # Cria log de scraping
        await db.create_scrape_log(
            source_id="all",
            status="success" if total_items > 0 else "error",
            items_extracted=total_items,
            items_failed=len(total_errors),
            error_message="\n".join(total_errors[:5]) if total_errors else None,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow()
        )

        return {
            "status": "success",
            "sources_processed": len(results),
            "total_items_saved": total_items,
            "total_errors": len(total_errors),
            "results": results
        }

    def _should_scrape(self, source: Dict) -> bool:
        """Verifica se uma fonte precisa ser scrapeada."""
        if not source.get("is_active"):
            return False

        last_scraped = source.get("last_scraped_at")
        frequency = source.get("scrape_frequency_hours", 24)

        if not last_scraped:
            return True

        # Verifica se passou o tempo
        from datetime import datetime, timedelta
        if isinstance(last_scraped, str):
            last_scraped = datetime.fromisoformat(last_scraped.replace("Z", "+00:00"))

        next_scrape = last_scraped + timedelta(hours=frequency)
        return datetime.utcnow() > next_scrape.replace(tzinfo=None)


# Instância global
scraper_service = ScraperService()