"""
Router de Knowledge Base.
"""
from fastapi import APIRouter, HTTPException, Depends, Header
from typing import List, Optional
from uuid import UUID

from app.models.knowledge import Knowledge, KnowledgeCreate, KnowledgeUpdate
from app.services.api_key_service import APIKeyService
from database.database import db

router = APIRouter()
api_key_service = APIKeyService()


async def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    """
    Verifica se a API Key é válida.
    """
    if not await api_key_service.verify_key(x_api_key):
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired API key"
        )
    return True


async def verify_master_key(x_master_key: str = Header(..., alias="X-Master-Key")):
    """
    Verifica se a master key é válida.
    """
    from app.config import get_settings
    settings = get_settings()

    if x_master_key != settings.api_master_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid master key"
        )
    return True


@router.post("/knowledge", response_model=Knowledge)
async def create_knowledge(
    data: KnowledgeCreate,
    _: bool = Depends(verify_master_key)
):
    """
    Cria novo conhecimento na base.

    Requer header X-Master-Key.

    - **titulo**: Título do conhecimento
    - **conteudo**: Conteúdo completo
    - **source_id**: ID da fonte (opcional)
    - **categoria**: Categoria (opcional)
    - **tags**: Lista de tags (opcional)
    - **url_original**: URL de origem (opcional)
    - **metadata**: Metadados adicionais (opcional)
    """
    try:
        # Detecta categoria automaticamente se não fornecida
        if not data.categoria:
            from app.utils.helpers import parse_category
            data.categoria = parse_category(data.conteudo)

        # Extrai tags automaticamente se não fornecidas
        if not data.tags:
            from app.utils.helpers import extract_tags
            data.tags = extract_tags(data.conteudo)

        result = await db.create_knowledge(
            titulo=data.titulo,
            conteudo=data.conteudo,
            source_id=str(data.source_id) if data.source_id else None,
            categoria=data.categoria,
            tags=data.tags,
            url_original=data.url_original,
            metadata=data.metadata
        )

        if not result:
            raise HTTPException(
                status_code=500,
                detail="Failed to create knowledge"
            )

        # Gera embedding em background
        # TODO: Implementar geração de embedding assíncrona

        return Knowledge(**result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create knowledge: {str(e)}"
        )


@router.get("/knowledge", response_model=List[Knowledge])
async def list_knowledge(
    limit: int = 50,
    offset: int = 0,
    categoria: Optional[str] = None,
    source_id: Optional[str] = None,
    _: bool = Depends(verify_api_key)
):
    """
    Lista conhecimentos com filtros.

    Requer header X-API-Key.

    - **limit**: Número máximo de resultados
    - **offset**: Offset para paginação
    - **categoria**: Filtrar por categoria
    - **source_id**: Filtrar por fonte
    """
    results = await db.list_knowledge(
        limit=limit,
        offset=offset,
        categoria=categoria,
        source_id=source_id
    )
    return [Knowledge(**r) for r in results]


@router.get("/knowledge/{knowledge_id}", response_model=Knowledge)
async def get_knowledge(
    knowledge_id: str,
    _: bool = Depends(verify_api_key)
):
    """
    Busca conhecimento por ID.

    Requer header X-API-Key.
    """
    result = await db.get_knowledge(knowledge_id)

    if not result:
        raise HTTPException(
            status_code=404,
            detail="Knowledge not found"
        )

    return Knowledge(**result)


@router.put("/knowledge/{knowledge_id}", response_model=Knowledge)
async def update_knowledge(
    knowledge_id: str,
    data: KnowledgeUpdate,
    _: bool = Depends(verify_master_key)
):
    """
    Atualiza conhecimento.

    Requer header X-Master-Key.
    """
    # Busca conhecimento existente
    existing = await db.get_knowledge(knowledge_id)
    if not existing:
        raise HTTPException(
            status_code=404,
            detail="Knowledge not found"
        )

    # Prepara dados para atualização
    update_fields = []
    update_values = []
    param_idx = 1

    if data.titulo is not None:
        update_fields.append(f"titulo = ${param_idx}")
        update_values.append(data.titulo)
        param_idx += 1

    if data.conteudo is not None:
        update_fields.append(f"conteudo = ${param_idx}")
        update_values.append(data.conteudo)
        param_idx += 1

    if data.categoria is not None:
        update_fields.append(f"categoria = ${param_idx}")
        update_values.append(data.categoria)
        param_idx += 1

    if data.tags is not None:
        update_fields.append(f"tags = ${param_idx}")
        update_values.append(data.tags)
        param_idx += 1

    if data.metadata is not None:
        import json
        update_fields.append(f"metadata = ${param_idx}")
        update_values.append(json.dumps(data.metadata))
        param_idx += 1

    if not update_fields:
        raise HTTPException(
            status_code=400,
            detail="No fields to update"
        )

    update_values.append(knowledge_id)
    query = f"UPDATE knowledge_base SET {', '.join(update_fields)}, updated_at = NOW() WHERE id = ${param_idx} RETURNING *"

    result = await db.fetchrow(query, *update_values)

    if not result:
        raise HTTPException(
            status_code=500,
            detail="Failed to update knowledge"
        )

    return Knowledge(**dict(result))


@router.delete("/knowledge/{knowledge_id}")
async def delete_knowledge(
    knowledge_id: str,
    _: bool = Depends(verify_master_key)
):
    """
    Deleta conhecimento.

    Requer header X-Master-Key.
    """
    success = await db.delete_knowledge(knowledge_id)

    if not success:
        raise HTTPException(
            status_code=404,
            detail="Knowledge not found"
        )

    return {"success": True, "message": "Knowledge deleted"}


@router.get("/categories")
async def list_categories(_: bool = Depends(verify_api_key)):
    """
    Lista todas as categorias disponíveis.

    Requer header X-API-Key.
    """
    from app.config import KNOWLEDGE_CATEGORIES
    return {
        "success": True,
        "categories": KNOWLEDGE_CATEGORIES
    }