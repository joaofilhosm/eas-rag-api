"""
Serviço de gestão de API Keys.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime

from database.database import db


class APIKeyService:
    """Serviço para gerenciar API Keys."""

    def __init__(self):
        self.db = db

    async def create_key(
        self,
        key_hash: str,
        name: str,
        description: Optional[str] = None,
        email: Optional[str] = None,
        expires_at: Optional[datetime] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Cria nova API Key.

        Args:
            key_hash: Hash MD5 da key
            name: Nome identificador
            description: Descrição opcional
            email: Email do proprietário
            expires_at: Data de expiração

        Returns:
            Dados da key criada
        """
        return await self.db.create_api_key(
            key_hash=key_hash,
            name=name,
            description=description,
            email=email,
            expires_at=expires_at.isoformat() if expires_at else None
        )

    async def get_key(self, key_id: str) -> Optional[Dict[str, Any]]:
        """
        Busca API Key por ID.

        Args:
            key_id: ID da key

        Returns:
            Dados da key
        """
        result = await self.db.fetchrow(
            "SELECT * FROM api_keys WHERE id = $1", key_id
        )
        return dict(result) if result else None

    async def get_key_by_hash(self, key_hash: str) -> Optional[Dict[str, Any]]:
        """
        Busca API Key por hash.

        Args:
            key_hash: Hash MD5 da key

        Returns:
            Dados da key
        """
        return await self.db.get_api_key_by_hash(key_hash)

    async def list_keys(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Lista todas as API Keys.

        Args:
            active_only: Se deve listar apenas ativas

        Returns:
            Lista de keys
        """
        return await self.db.list_api_keys(active_only=active_only)

    async def deactivate_key(self, key_id: str) -> bool:
        """
        Desativa uma API Key.

        Args:
            key_id: ID da key

        Returns:
            True se desativada
        """
        result = await self.db.execute(
            "UPDATE api_keys SET is_active = false WHERE id = $1", key_id
        )
        return "UPDATE 1" in result

    async def verify_key(self, api_key: str) -> bool:
        """
        Verifica se uma API Key é válida.

        Args:
            api_key: API Key completa

        Returns:
            True se válida e ativa
        """
        from app.utils.helpers import hash_api_key, validate_api_key

        # Valida formato
        if not validate_api_key(api_key):
            return False

        # Busca pelo hash
        key_hash = hash_api_key(api_key)
        key_data = await self.get_key_by_hash(key_hash)

        if not key_data:
            return False

        # Verifica se está ativa
        if not key_data.get("is_active"):
            return False

        # Verifica expiração
        if key_data.get("expires_at"):
            expires_at = datetime.fromisoformat(key_data["expires_at"])
            if datetime.utcnow() > expires_at:
                return False

        # Atualiza último uso
        await self.db.update_last_used(key_hash)

        return True