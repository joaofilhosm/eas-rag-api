"""
Router de Busca RAG.
"""
from fastapi import APIRouter, HTTPException, Depends, Header
from typing import List, Optional

from app.models.knowledge import KnowledgeSearch, KnowledgeSearchResponse, KnowledgeSearchResult, Knowledge
from app.services.rag import RAGService
from app.services.api_key_service import APIKeyService

router = APIRouter()
rag_service = RAGService()
api_key_service = APIKeyService()


async def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    """
    Verifica se a API Key é válida.

    Args:
        x_api_key: API Key do header

    Returns:
        True se válida

    Raises:
        HTTPException: Se key inválida
    """
    if not await api_key_service.verify_key(x_api_key):
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired API key"
        )
    return True


@router.post("/search", response_model=KnowledgeSearchResponse)
async def search_knowledge(
    query: KnowledgeSearch,
    _: bool = Depends(verify_api_key)
):
    """
    Busca semântica na base de conhecimento.

    Requer header X-API-Key.

    - **query**: Texto da busca
    - **limit**: Número máximo de resultados (default: 10)
    - **offset**: Offset para paginação
    - **categoria**: Filtrar por categoria (opcional)
    - **tags**: Filtrar por tags (opcional)
    - **min_similarity**: Similaridade mínima (0-1, default: 0.5)
    """
    try:
        results = await rag_service.search(
            query=query.query,
            limit=query.limit,
            offset=query.offset,
            categoria=query.categoria,
            tags=query.tags,
            min_similarity=query.min_similarity
        )

        return KnowledgeSearchResponse(
            results=results,
            total=len(results),
            query=query.query,
            limit=query.limit,
            offset=query.offset,
            search_type="semantic"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )


@router.post("/search/similar/{knowledge_id}")
async def find_similar(
    knowledge_id: str,
    limit: int = 5,
    _: bool = Depends(verify_api_key)
):
    """
    Encontra documentos similares a um conhecimento.

    Requer header X-API-Key.

    - **knowledge_id**: ID do conhecimento base
    - **limit**: Número máximo de resultados
    """
    try:
        results = await rag_service.find_similar(
            knowledge_id=knowledge_id,
            limit=limit
        )

        return {
            "success": True,
            "results": results,
            "total": len(results)
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to find similar: {str(e)}"
        )


@router.get("/search/suggestions")
async def get_search_suggestions(
    prefix: str,
    limit: int = 10,
    _: bool = Depends(verify_api_key)
):
    """
    Retorna sugestões de busca baseadas no prefixo.

    Requer header X-API-Key.

    - **prefix**: Prefixo para busca
    - **limit**: Número máximo de sugestões
    """
    try:
        suggestions = await rag_service.get_suggestions(
            prefix=prefix,
            limit=limit
        )

        return {
            "success": True,
            "suggestions": suggestions
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get suggestions: {str(e)}"
        )