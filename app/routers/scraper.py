"""
Router de Controle do Scraper.
"""
from fastapi import APIRouter, HTTPException, Depends, Header
from typing import List, Optional
from datetime import datetime

from app.models.scraper import ScraperStatus, ScraperResult, SourceConfig, Source, ScraperStart, ScrapeLog
from app.services.api_key_service import APIKeyService
from database.database import db
from app.config import get_settings

router = APIRouter()
api_key_service = APIKeyService()
settings = get_settings()


def verify_master_key(master_key: str = Header(..., alias="X-Master-Key")):
    """Verifica master key."""
    if master_key != settings.api_master_key:
        raise HTTPException(status_code=401, detail="Invalid master key")
    return True


# Estado global do scraper
scraper_state = {
    "is_running": False,
    "current_source": None,
    "last_run_at": None,
    "last_status": None
}


@router.get("/scraper/status", response_model=ScraperStatus)
async def get_scraper_status(_: bool = Depends(verify_master_key)):
    """
    Retorna status atual do scraper.

    Requer header X-Master-Key.
    """
    # Busca estatísticas
    stats = await db.get_stats()

    # Conta fontes ativas
    sources = await db.get_sources(active_only=True)

    # Conta fontes pendentes
    pending_sources = await db.fetch(
        "SELECT COUNT(*) FROM sources WHERE is_active = true AND (last_scraped_at IS NULL OR last_scraped_at < NOW() - INTERVAL '1 day' * scrape_frequency_hours)"
    )
    pending_count = pending_sources[0]["count"] if pending_sources else 0

    return ScraperStatus(
        is_running=scraper_state["is_running"],
        current_source=scraper_state["current_source"],
        last_run_at=scraper_state.get("last_run_at"),
        last_status=scraper_state.get("last_status"),
        total_items=stats.get("total_knowledge", 0),
        sources_active=len(sources),
        sources_pending=pending_count
    )


@router.post("/scraper/start")
async def start_scraper(
    data: ScraperStart,
    _: bool = Depends(verify_master_key)
):
    """
    Inicia scraping manual.

    Requer header X-Master-Key.

    - **source_ids**: IDs específicos das fontes (opcional)
    - **force**: Forçar execução mesmo se já executou
    """
    if scraper_state["is_running"]:
        raise HTTPException(
            status_code=409,
            detail="Scraper is already running"
        )

    # TODO: Implementar execução real do scraper
    # Por enquanto retorna confirmação

    return {
        "success": True,
        "message": "Scraper started",
        "source_ids": data.source_ids,
        "force": data.force
    }


@router.post("/scraper/stop")
async def stop_scraper(_: bool = Depends(verify_master_key)):
    """
    Para o scraper em execução.

    Requer header X-Master-Key.
    """
    if not scraper_state["is_running"]:
        raise HTTPException(
            status_code=400,
            detail="Scraper is not running"
        )

    # TODO: Implementar parada real
    scraper_state["is_running"] = False
    scraper_state["current_source"] = None

    return {
        "success": True,
        "message": "Scraper stopped"
    }


@router.get("/sources", response_model=List[Source])
async def list_sources(
    active_only: bool = True,
    _: bool = Depends(verify_master_key)
):
    """
    Lista todas as fontes de dados.

    Requer header X-Master-Key.
    """
    sources = await db.get_sources(active_only=active_only)
    return [Source(**s) for s in sources]


@router.post("/sources", response_model=Source)
async def create_source(
    data: SourceConfig,
    _: bool = Depends(verify_master_key)
):
    """
    Cria nova fonte de dados.

    Requer header X-Master-Key.

    - **name**: Nome da fonte
    - **url**: URL base
    - **type**: Tipo (fitness, scientific, medical, general)
    - **scrape_frequency_hours**: Frequência de scraping em horas
    """
    result = await db.create_source(
        name=data.name,
        url=data.url,
        source_type=data.type.value,
        scrape_frequency_hours=data.scrape_frequency_hours
    )

    if not result:
        raise HTTPException(
            status_code=500,
            detail="Failed to create source"
        )

    return Source(**result)


@router.get("/sources/{source_id}", response_model=Source)
async def get_source(
    source_id: str,
    _: bool = Depends(verify_master_key)
):
    """
    Busca fonte por ID.

    Requer header X-Master-Key.
    """
    result = await db.get_source(source_id)

    if not result:
        raise HTTPException(
            status_code=404,
            detail="Source not found"
        )

    return Source(**result)


@router.put("/sources/{source_id}/deactivate")
async def deactivate_source(
    source_id: str,
    _: bool = Depends(verify_master_key)
):
    """
    Desativa uma fonte.

    Requer header X-Master-Key.
    """
    result = await db.execute(
        "UPDATE sources SET is_active = false WHERE id = $1",
        source_id
    )

    if "UPDATE 1" not in result:
        raise HTTPException(
            status_code=404,
            detail="Source not found"
        )

    return {"success": True, "message": "Source deactivated"}


@router.get("/scraper/logs", response_model=List[ScrapeLog])
async def get_scraper_logs(
    source_id: Optional[str] = None,
    limit: int = 50,
    _: bool = Depends(verify_master_key)
):
    """
    Lista logs de scraping.

    Requer header X-Master-Key.

    - **source_id**: Filtrar por fonte (opcional)
    - **limit**: Número máximo de logs
    """
    logs = await db.get_scrape_logs(source_id=source_id, limit=limit)
    return [ScrapeLog(**log) for log in logs]