"""
Scheduler para execução contínua do scraper.
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import get_settings, SCRAPER_SOURCES
from database import db
from scraper.sources.dicasdetreino import DicasDeTreinoScraper
from scraper.sources.hipertrofia_org import HipertrofiaOrgScraper
from scraper.sources.scientific import ScientificScraper


class ScraperScheduler:
    """Scheduler para executar scrapers periodicamente."""

    def __init__(self):
        """Inicializa o scheduler."""
        self.settings = get_settings()
        self.scheduler = AsyncIOScheduler()
        self.running_scrapers: Dict[str, bool] = {}
        self.last_run: Dict[str, datetime] = {}

    def get_scraper_class(self, source_type: str):
        """
        Retorna a classe de scraper apropriada.

        Args:
            source_type: Tipo da fonte

        Returns:
            Classe do scraper
        """
        scraper_map = {
            "fitness": [DicasDeTreinoScraper, HipertrofiaOrgScraper],
            "scientific": ScientificScraper,
        }

        return scraper_map.get(source_type, DicasDeTreinoScraper)

    async def run_scraper(self, source: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executa scraping para uma fonte específica.

        Args:
            source: Configuração da fonte

        Returns:
            Resultado do scraping
        """
        source_id = str(source.get("id", ""))
        source_name = source.get("name", "Unknown")

        # Verifica se já está rodando
        if self.running_scrapers.get(source_id):
            return {
                "status": "skipped",
                "reason": "Already running",
                "source": source_name
            }

        self.running_scrapers[source_id] = True
        self.last_run[source_id] = datetime.utcnow()

        try:
            # Instancia o scraper correto
            source_type = source.get("type", "fitness")
            scraper_class = self.get_scraper_class(source_type)

            if source_type == "scientific":
                scraper = scraper_class(source)
            elif source_type == "fitness":
                # Escolhe o scraper baseado na URL
                url = source.get("url", "")
                if "dicasdetreino" in url:
                    scraper = DicasDeTreinoScraper(source)
                elif "hipertrofia" in url:
                    scraper = HipertrofiaOrgScraper(source)
                else:
                    scraper = DicasDeTreinoScraper(source)
            else:
                scraper = DicasDeTreinoScraper(source)

            # Executa scraping
            result = await scraper.scrape(max_pages=50)

            # Fecha cliente HTTP
            await scraper.close()

            return {
                "status": "success",
                "source": source_name,
                "result": result
            }

        except Exception as e:
            return {
                "status": "error",
                "source": source_name,
                "error": str(e)
            }

        finally:
            self.running_scrapers[source_id] = False

    async def run_all_scrapers(self) -> List[Dict[str, Any]]:
        """
        Executa scraping para todas as fontes ativas.

        Returns:
            Lista de resultados
        """
        results = []

        # Busca fontes ativas que precisam de scraping
        sources = await db.client.table("v_sources_needing_scrape").select("*").execute()

        if not sources.data:
            print("Nenhuma fonte precisa de scraping no momento")
            return results

        for source in sources.data:
            print(f"Executando scraper para: {source['name']}")

            result = await self.run_scraper(source)
            results.append(result)

            # Delay entre fontes
            await asyncio.sleep(self.settings.scraper_delay_seconds)

        return results

    async def run_scrapers_by_type(self, source_type: str) -> List[Dict[str, Any]]:
        """
        Executa scrapers de um tipo específico.

        Args:
            source_type: Tipo da fonte (fitness, scientific)

        Returns:
            Lista de resultados
        """
        results = []

        sources = await db.get_sources(active_only=True)
        filtered_sources = [s for s in sources if s.get("type") == source_type]

        for source in filtered_sources:
            result = await self.run_scraper(source)
            results.append(result)
            await asyncio.sleep(self.settings.scraper_delay_seconds)

        return results

    def start(self):
        """Inicia o scheduler."""
        # Job para rodar todos os scrapers a cada 24 horas
        self.scheduler.add_job(
            self.run_all_scrapers,
            IntervalTrigger(hours=24),
            id="daily_scrape",
            replace_existing=True
        )

        # Job para verificar fontes a cada hora
        self.scheduler.add_job(
            self.check_pending_sources,
            IntervalTrigger(hours=1),
            id="check_sources",
            replace_existing=True
        )

        self.scheduler.start()
        print("Scheduler iniciado")

    def stop(self):
        """Para o scheduler."""
        self.scheduler.shutdown()
        print("Scheduler parado")

    async def check_pending_sources(self):
        """Verifica se há fontes pendentes de scraping."""
        sources = await db.client.table("v_sources_needing_scrape").select("count").execute()

        if sources.data and sources.data[0].get("count", 0) > 0:
            print(f"Há {sources.data[0]['count']} fontes pendentes de scraping")

    def get_status(self) -> Dict[str, Any]:
        """
        Retorna status do scheduler.

        Returns:
            Dicionário com status
        """
        jobs = self.scheduler.get_jobs()

        return {
            "running": self.scheduler.running,
            "jobs": [
                {
                    "id": job.id,
                    "next_run": str(job.next_run_time) if job.next_run_time else None
                }
                for job in jobs
            ],
            "active_scrapers": [
                source_id for source_id, running in self.running_scrapers.items() if running
            ],
            "last_runs": {
                source_id: dt.isoformat() if dt else None
                for source_id, dt in self.last_run.items()
            }
        }


# Instância global
scheduler = ScraperScheduler()


def get_scheduler() -> ScraperScheduler:
    """Retorna instância do scheduler."""
    return scheduler