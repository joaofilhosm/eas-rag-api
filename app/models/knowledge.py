"""
Modelos Pydantic para Base de Conhecimento.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field
from enum import Enum


class KnowledgeCategory(str, Enum):
    """Categorias de conhecimento."""
    TREINO = "treino"
    NUTRICAO = "nutricao"
    SUPLEMENTACAO = "suplementacao"
    HORMONIOS = "hormonios"
    ESTEROIDES = "esteroides"
    MEDICO = "medico"
    CIENTIFICO = "cientifico"
    TECNICO = "tecnico"
    GERAL = "geral"


class KnowledgeBase(BaseModel):
    """Modelo base para conhecimento."""
    titulo: str = Field(..., min_length=1, max_length=500, description="Título do conhecimento")
    conteudo: str = Field(..., min_length=1, description="Conteúdo completo do conhecimento")
    categoria: Optional[str] = Field(None, max_length=100, description="Categoria do conhecimento")
    tags: List[str] = Field(default_factory=list, description="Tags associadas")
    url_original: Optional[str] = Field(None, max_length=1000, description="URL de origem")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Metadados adicionais")


class KnowledgeCreate(KnowledgeBase):
    """Modelo para criar novo conhecimento."""
    source_id: Optional[UUID] = Field(None, description="ID da fonte de dados")


class KnowledgeUpdate(BaseModel):
    """Modelo para atualizar conhecimento."""
    titulo: Optional[str] = Field(None, min_length=1, max_length=500)
    conteudo: Optional[str] = Field(None, min_length=1)
    categoria: Optional[str] = Field(None, max_length=100)
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class Knowledge(KnowledgeBase):
    """Modelo completo de conhecimento."""
    id: UUID
    source_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class KnowledgeSearch(BaseModel):
    """Parâmetros de busca na base de conhecimento."""
    query: str = Field(..., min_length=1, description="Texto da busca")
    limit: int = Field(default=10, ge=1, le=100, description="Número máximo de resultados")
    offset: int = Field(default=0, ge=0, description="Offset para paginação")
    categoria: Optional[str] = Field(None, description="Filtrar por categoria")
    tags: Optional[List[str]] = Field(None, description="Filtrar por tags")
    source_id: Optional[UUID] = Field(None, description="Filtrar por fonte")
    min_similarity: float = Field(default=0.5, ge=0, le=1, description="Similaridade mínima (0-1)")


class KnowledgeSearchResult(BaseModel):
    """Resultado da busca com similaridade."""
    knowledge: Knowledge
    similarity: float = Field(..., description="Score de similaridade (0-1)")
    embedding_used: bool = Field(default=True, description="Se usou busca vetorial")


class KnowledgeSearchResponse(BaseModel):
    """Resposta completa da busca."""
    results: List[KnowledgeSearchResult]
    total: int
    query: str
    limit: int
    offset: int
    search_type: str = Field(default="semantic", description="Tipo de busca: semantic ou keyword")