"""ProviderRepository — SQLAlchemy implementation of ProviderRepositoryPort."""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from vera_core.errors import ConflictError
from vera_core.models.ids import ProviderConnectionId, TenantId, UserId
from vera_core.models.provider import (
    ConnectionStatus,
    ModelInfo,
    ProviderConnection,
    ProviderKind,
)

from vera_db.models.provider import ProviderConnectionRow, ProviderModelCacheRow


class ProviderRepository:
    """Persists provider connections and their cached model lists.

    Takes an :class:`AsyncSession`; the caller owns the transaction so a
    connection insert and the matching Vault write can commit atomically.
    """

    def __init__(self, *, session: AsyncSession) -> None:
        self._session = session

    async def create_connection(self, *, conn: ProviderConnection) -> ProviderConnection:
        row = self._to_row(conn)
        self._session.add(row)
        try:
            await self._session.flush()
        except IntegrityError as exc:  # unique (user_id, display_name)
            raise ConflictError(
                f"A provider connection named {conn.display_name!r} already exists"
            ) from exc
        await self._session.refresh(row)
        return self._to_domain(row)

    async def get_connection(
        self, *, id: ProviderConnectionId, tenant_id: TenantId
    ) -> ProviderConnection | None:
        stmt = (
            select(ProviderConnectionRow)
            .where(
                ProviderConnectionRow.id == id,
                ProviderConnectionRow.tenant_id == tenant_id,
            )
            .options(selectinload(ProviderConnectionRow.models))
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        if row is None:
            return None
        return self._to_domain(row, models=row.models)

    async def list_connections(self, *, user_id: UserId) -> list[ProviderConnection]:
        stmt = (
            select(ProviderConnectionRow)
            .where(ProviderConnectionRow.user_id == user_id)
            .order_by(ProviderConnectionRow.created_at.desc())
            .options(selectinload(ProviderConnectionRow.models))
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [self._to_domain(row, models=row.models) for row in rows]

    async def update_connection(self, *, conn: ProviderConnection) -> ProviderConnection:
        stmt = select(ProviderConnectionRow).where(
            ProviderConnectionRow.id == conn.id,
            ProviderConnectionRow.tenant_id == conn.tenant_id,
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        if row is None:
            raise ConflictError(f"Provider connection {conn.id} not found for update")
        row.status = conn.status.value
        row.display_name = conn.display_name
        row.last_error = conn.last_error
        row.last_validated_at = conn.last_validated_at
        try:
            await self._session.flush()
        except IntegrityError as exc:
            raise ConflictError(
                f"A provider connection named {conn.display_name!r} already exists"
            ) from exc
        await self._session.refresh(row)
        return self._to_domain(row)

    async def delete_connection(self, *, id: ProviderConnectionId, tenant_id: TenantId) -> None:
        await self._session.execute(
            delete(ProviderConnectionRow).where(
                ProviderConnectionRow.id == id,
                ProviderConnectionRow.tenant_id == tenant_id,
            )
        )

    async def replace_model_cache(
        self, *, provider_connection_id: ProviderConnectionId, models: list[ModelInfo]
    ) -> None:
        await self._session.execute(
            delete(ProviderModelCacheRow).where(
                ProviderModelCacheRow.provider_connection_id == provider_connection_id
            )
        )
        await self._session.flush()
        self._session.add_all(
            ProviderModelCacheRow(
                provider_connection_id=provider_connection_id,
                model_id=m.model_id,
                display_name=m.display_name,
                context_window=m.context_window,
                input_price_per_m=m.input_price_per_m,
                output_price_per_m=m.output_price_per_m,
                supports_json_mode=m.supports_json_mode,
                supports_function_calling=m.supports_function_calling,
                supports_vision=m.supports_vision,
            )
            for m in models
        )
        await self._session.flush()

    # ── mapping ──────────────────────────────────────────────────────────────

    @staticmethod
    def _to_row(conn: ProviderConnection) -> ProviderConnectionRow:
        return ProviderConnectionRow(
            id=conn.id,
            tenant_id=conn.tenant_id,
            user_id=conn.user_id,
            kind=conn.kind.value,
            display_name=conn.display_name,
            base_url=conn.base_url,
            api_key_ref=conn.api_key_ref,
            status=conn.status.value,
            last_validated_at=conn.last_validated_at,
            last_error=conn.last_error,
        )

    @staticmethod
    def _model_to_domain(row: ProviderModelCacheRow) -> ModelInfo:
        return ModelInfo(
            model_id=row.model_id,
            display_name=row.display_name,
            context_window=row.context_window,
            input_price_per_m=row.input_price_per_m,
            output_price_per_m=row.output_price_per_m,
            supports_json_mode=row.supports_json_mode,
            supports_function_calling=row.supports_function_calling,
            supports_vision=row.supports_vision,
        )

    @classmethod
    def _to_domain(
        cls,
        row: ProviderConnectionRow,
        models: list[ProviderModelCacheRow] | None = None,
    ) -> ProviderConnection:
        available = [cls._model_to_domain(m) for m in models] if models is not None else None
        return ProviderConnection(
            id=ProviderConnectionId(row.id),
            tenant_id=TenantId(row.tenant_id),
            user_id=UserId(row.user_id),
            kind=ProviderKind(row.kind),
            display_name=row.display_name,
            base_url=row.base_url,
            api_key_ref=row.api_key_ref,
            status=ConnectionStatus(row.status),
            available_models=available,
            created_at=row.created_at,
            last_validated_at=row.last_validated_at,
            last_error=row.last_error,
        )


__all__ = ["ProviderRepository"]
