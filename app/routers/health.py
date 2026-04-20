"""
Router de Health Check.
"""
from fastapi import APIRouter, Depends
from datetime import datetime
from typing import Dict, Any

from database import db

router = APIRouter()


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Health check básico.

    Retorna status da API.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "EAS API RAG"
    }


@router.get("/health/detailed")
async def detailed_health_check() -> Dict[str, Any]:
    """
    Health check detalhado.

    Verifica conexão com banco de dados e serviços externos.
    """
    health = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {}
    }

    # Verifica banco de dados
    try:
        stats = await db.get_stats()
        health["services"]["database"] = {
            "status": "healthy",
            "stats": stats
        }
    except Exception as e:
        health["services"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health["status"] = "degraded"

    return health


@router.get("/stats")
async def get_statistics() -> Dict[str, Any]:
    """
    Retorna estatísticas da API.
    """
    stats = await db.get_stats()
    return {
        "success": True,
        "data": stats
    }