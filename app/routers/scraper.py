"""
Router de Controle do Scraper.
"""
from fastapi import APIRouter, HTTPException, Depends, Header, BackgroundTasks
from typing import List, Optional
from datetime import datetime

from app.models.scraper import ScraperStatus, ScraperResult, SourceConfig, Source, ScraperStart, ScrapeLog
from app.services.api_key_service import APIKeyService
from app.services.scraper_service import scraper_service
from database.database import db
from app.config import get_settings

router = APIRouter()
api_key_service = APIKeyService()
settings = get_settings()

# Estado global do scraper
scraper_state = {
    "is_running": False,
    "current_source": None,
    "last_run_at": None,
    "last_status": None,
    "last_error": None,
    "total_items": 0
}


def verify_master_key(master_key: str = Header(..., alias="X-Master-Key")):
    """Verifica master key."""
    if master_key != settings.api_master_key:
        raise HTTPException(status_code=401, detail="Invalid master key")
    return True


@router.get("/scraper/status", response_model=ScraperStatus)
async def get_scraper_status(_: bool = Depends(verify_master_key)):
    """
    Retorna status atual do scraper.

    Requer header X-Master-Key.
    """
    stats = await db.get_stats()
    sources = await db.get_sources(active_only=True)

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
    background_tasks: BackgroundTasks,
    _: bool = Depends(verify_master_key)
):
    """
    Inicia scraping de todas as fontes ou fontes específicas.

    Requer header X-Master-Key.

    - **source_ids**: IDs específicos das fontes (opcional)
    - **force**: Forçar execução mesmo se já executou
    """
    if scraper_state["is_running"]:
        raise HTTPException(
            status_code=409,
            detail="Scraper is already running"
        )

    # Marca como rodando
    scraper_state["is_running"] = True
    scraper_state["last_run_at"] = datetime.utcnow()
    scraper_state["last_status"] = "running"

    # Executa em background
    background_tasks.add_task(
        run_scraper_task,
        data.source_ids,
        data.force
    )

    return {
        "success": True,
        "message": "Scraper started in background",
        "source_ids": data.source_ids,
        "force": data.force
    }


async def run_scraper_task(source_ids: Optional[List[str]] = None, force: bool = False):
    """Task de execução do scraper."""
    try:
        import aiohttp

        async with aiohttp.ClientSession(
            headers={"User-Agent": settings.scraper_user_agent},
            timeout=aiohttp.ClientTimeout(total=30)
        ) as session:
            sources = await db.get_sources(active_only=True)

            # Filtra por IDs se especificado
            if source_ids:
                sources = [s for s in sources if str(s["id"]) in source_ids]

            total_items = 0

            for source in sources:
                scraper_state["current_source"] = source["name"]

                result = await scraper_service.scrape_source(source, session)
                total_items += result.get("items_saved", 0)

                # Log de cada fonte
                await db.create_scrape_log(
                    source_id=source["id"],
                    status=result.get("status", "success"),
                    items_extracted=result.get("items_saved", 0),
                    items_failed=len(result.get("errors", [])),
                    error_message="\n".join(result.get("errors", []))[:500] if result.get("errors") else None,
                    started_at=datetime.utcnow(),
                    completed_at=datetime.utcnow()
                )

            scraper_state["last_status"] = "success"
            scraper_state["total_items"] = total_items

    except Exception as e:
        scraper_state["last_status"] = "error"
        scraper_state["last_error"] = str(e)
        import traceback
        traceback.print_exc()
    finally:
        scraper_state["is_running"] = False
        scraper_state["current_source"] = None


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
        url=str(data.url),
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


@router.put("/sources/{source_id}/activate")
async def activate_source(
    source_id: str,
    _: bool = Depends(verify_master_key)
):
    """
    Ativa uma fonte.

    Requer header X-Master-Key.
    """
    result = await db.execute(
        "UPDATE sources SET is_active = true WHERE id = $1",
        source_id
    )

    if "UPDATE 1" not in result:
        raise HTTPException(
            status_code=404,
            detail="Source not found"
        )

    return {"success": True, "message": "Source activated"}


@router.post("/sources/{source_id}/scrape")
async def scrape_single_source(
    source_id: str,
    background_tasks: BackgroundTasks,
    _: bool = Depends(verify_master_key)
):
    """
    Executa scraping de uma fonte específica.

    Requer header X-Master-Key.
    """
    source = await db.get_source(source_id)

    if not source:
        raise HTTPException(
            status_code=404,
            detail="Source not found"
        )

    if scraper_state["is_running"]:
        raise HTTPException(
            status_code=409,
            detail="Scraper is already running"
        )

    # Executa em background
    background_tasks.add_task(
        run_single_scrape,
        source
    )

    return {
        "success": True,
        "message": f"Scraping started for {source['name']}",
        "source_id": source_id
    }


async def run_single_scrape(source: dict):
    """Executa scraping de uma fonte."""
    try:
        import aiohttp

        async with aiohttp.ClientSession(
            headers={"User-Agent": settings.scraper_user_agent},
            timeout=aiohttp.ClientTimeout(total=30)
        ) as session:
            scraper_state["is_running"] = True
            scraper_state["current_source"] = source["name"]

            result = await scraper_service.scrape_source(source, session)

            await db.create_scrape_log(
                source_id=source["id"],
                status=result.get("status", "success"),
                items_extracted=result.get("items_saved", 0),
                items_failed=len(result.get("errors", [])),
                error_message="\n".join(result.get("errors", []))[:500] if result.get("errors") else None,
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow()
            )

            scraper_state["last_status"] = "success"

    except Exception as e:
        scraper_state["last_status"] = "error"
        scraper_state["last_error"] = str(e)
        import traceback
        traceback.print_exc()
    finally:
        scraper_state["is_running"] = False
        scraper_state["current_source"] = None


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