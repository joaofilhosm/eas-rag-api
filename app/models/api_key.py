"""
Modelos Pydantic para API Keys.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, EmailStr


class APIKeyBase(BaseModel):
    """Modelo base para API Key."""
    name: str = Field(..., min_length=1, max_length=255, description="Nome identificador da key")
    description: Optional[str] = Field(None, description="Descrição da key")


class APIKeyCreate(APIKeyBase):
    """Modelo para criar nova API Key."""
    expires_at: Optional[datetime] = Field(None, description="Data de expiração (opcional)")
    email: Optional[EmailStr] = Field(None, description="Email do proprietário (opcional)")


class APIKey(APIKeyBase):
    """Modelo completo de API Key."""
    id: UUID
    key_hash: str = Field(..., description="Hash MD5 da key")
    is_active: bool = True
    created_at: datetime
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    email: Optional[str] = None

    class Config:
        from_attributes = True


class APIKeyResponse(BaseModel):
    """Resposta ao criar API Key (retorna a key completa uma única vez)."""
    id: UUID
    name: str
    key: str = Field(..., description="API Key completa (GUARDE COM CUIDADO - não será mostrada novamente)")
    key_hash: str
    is_active: bool
    created_at: datetime
    expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class APIKeyList(BaseModel):
    """Lista de API Keys (sem mostrar a key completa)."""
    id: UUID
    name: str
    description: Optional[str]
    is_active: bool
    created_at: datetime
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]

    class Config:
        from_attributes = True