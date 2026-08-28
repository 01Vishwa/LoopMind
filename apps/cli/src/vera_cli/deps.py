"""Dependency container — builds engine, sessionmaker, and HTTP client from the environment."""

from __future__ import annotations

from dataclasses import dataclass

import httpx
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from vera_db import DbConfig, build_direct_engine, make_sessionmaker


@dataclass
class Deps:
    """Live infrastructure handles for a single CLI invocation."""

    engine: AsyncEngine
    sessionmaker: async_sessionmaker[AsyncSession]
    http: httpx.AsyncClient


async def build_deps() -> Deps:
    """Construct real dependencies from ``VERA_DATABASE_URL*`` env vars."""
    cfg = DbConfig.from_env()
    engine = build_direct_engine(cfg.direct_url)
    return Deps(engine=engine, sessionmaker=make_sessionmaker(engine), http=httpx.AsyncClient())


async def aclose(deps: Deps) -> None:
    """Release the HTTP client and dispose the engine pool."""
    await deps.http.aclose()
    await deps.engine.dispose()


__all__ = ["Deps", "build_deps", "aclose"]
