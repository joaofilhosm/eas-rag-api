"""
Router de API Keys.
"""
from fastapi import APIRouter, HTTPException, Depends, Header
from typing import List, Optional
from datetime import datetime

from app.models.api_key import APIKeyCreate, APIKeyResponse, APIKeyList
from app.services.api_key_service import APIKeyService
from app.config import get_settings
from app.utils.helpers import generate_md5, hash_api_key

router = APIRouter()
settings = get_settings()
api_key_service = APIKeyService()


def verify_master_key(master_key: str = Header(..., alias="X-Master-Key")):
    """
    Verifica se a master key é válida.

    Args:
        master_key: Master key do header

    Returns:
        True se válida

    Raises:
        HTTPException: Se master key inválida
    """
    if master_key != settings.api_master_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid master key"
        )
    return True


@router.post("/api-keys", response_model=APIKeyResponse)
async def create_api_key(
    data: APIKeyCreate,
    _: bool = Depends(verify_master_key)
):
    """
    Cria nova API Key.

    Requer header X-Master-Key com a chave master.

    - **name**: Nome identificador da key
    - **description**: Descrição opcional
    - **expires_at**: Data de expiração opcional
    - **email**: Email do proprietário opcional
    """
    # Gera nova key
    api_key = generate_md5(prefix="eas")
    key_hash = hash_api_key(api_key)

    # Salva no banco
    result = await api_key_service.create_key(
        key_hash=key_hash,
        name=data.name,
        description=data.description,
        email=data.email,
        expires_at=data.expires_at
    )

    if not result:
        raise HTTPException(
            status_code=500,
            detail="Failed to create API key"
        )

    return APIKeyResponse(
        id=result["id"],
        name=result["name"],
        key=api_key,  # Retorna key completa APENAS na criação
        key_hash=result["key_hash"],
        is_active=result["is_active"],
        created_at=result["created_at"],
        expires_at=result.get("expires_at")
    )


@router.get("/api-keys", response_model=List[APIKeyList])
async def list_api_keys(
    active_only: bool = True,
    _: bool = Depends(verify_master_key)
):
    """
    Lista todas as API Keys.

    Requer header X-Master-Key.
    """
    keys = await api_key_service.list_keys(active_only=active_only)
    return [APIKeyList(**key) for key in keys]


@router.get("/api-keys/{key_id}", response_model=APIKeyList)
async def get_api_key(
    key_id: str,
    _: bool = Depends(verify_master_key)
):
    """
    Busca API Key por ID.

    Requer header X-Master-Key.
    """
    key = await api_key_service.get_key(key_id)
    if not key:
        raise HTTPException(
            status_code=404,
            detail="API key not found"
        )
    return APIKeyList(**key)


@router.delete("/api-keys/{key_id}")
async def deactivate_api_key(
    key_id: str,
    _: bool = Depends(verify_master_key)
):
    """
    Desativa uma API Key.

    Requer header X-Master-Key.
    """
    success = await api_key_service.deactivate_key(key_id)
    if not success:
        raise HTTPException(
            status_code=404,
            detail="API key not found"
        )
    return {"success": True, "message": "API key deactivated"}