"""
Modelos Pydantic para o Scraper.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field
from enum import Enum


class SourceType(str, Enum):
    """Tipos de fonte de dados."""
    FITNESS = "fitness"
    SCIENTIFIC = "scientific"
    MEDICAL = "medical"
    GENERAL = "general"


class ScrapeStatus(str, Enum):
    """Status de execução do scraper."""
    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    PARTIAL = "partial"


class SourceConfig(BaseModel):
    """Configuração de uma fonte de dados."""
    name: str = Field(..., description="Nome da fonte")
    url: str = Field(..., description="URL base da fonte")
    type: SourceType = Field(default=SourceType.GENERAL, description="Tipo da fonte")
    is_active: bool = Field(default=True, description="Se a fonte está ativa")
    scrape_frequency_hours: int = Field(default=24, ge=1, description="Frequência de scraping em horas")
    last_scraped_at: Optional[datetime] = None


class Source(SourceConfig):
    """Fonte de dados com ID."""
    id: UUID

    class Config:
        from_attributes = True


class ScraperResult(BaseModel):
    """Resultado de uma execução do scraper."""
    source_id: UUID
    source_name: str
    status: ScrapeStatus
    items_extracted: int = Field(default=0, description="Número de itens extraídos")
    items_failed: int = Field(default=0, description="Número de itens que falharam")
    error_message: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None

    class Config:
        from_attributes = True


class ScraperStatus(BaseModel):
    """Status atual do scraper."""
    is_running: bool
    current_source: Optional[str] = None
    last_run_at: Optional[datetime] = None
    last_status: Optional[ScrapeStatus] = None
    total_items: int = Field(default=0, description="Total de itens na base")
    sources_active: int = Field(default=0, description="Número de fontes ativas")
    sources_pending: int = Field(default=0, description="Fontes pendentes de scraping")


class ScraperStart(BaseModel):
    """Requisição para iniciar scraping."""
    source_ids: Optional[List[UUID]] = Field(None, description="IDs específicos das fontes (opcional)")
    force: bool = Field(default=False, description="Forçar execução mesmo se já executou hoje")


class ScrapeLog(BaseModel):
    """Log de execução do scraper."""
    id: UUID
    source_id: UUID
    status: ScrapeStatus
    items_extracted: int
    error_message: Optional[str]
    started_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True