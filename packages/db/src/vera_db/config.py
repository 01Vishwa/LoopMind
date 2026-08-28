"""Database configuration — reads Supabase Postgres DSNs from the environment."""

from __future__ import annotations

import os
from dataclasses import dataclass

from vera_core.errors import ValidationError

_POOLED_ENV = "VERA_DATABASE_URL"
_DIRECT_ENV = "VERA_DATABASE_URL_DIRECT"


@dataclass(frozen=True)
class DbConfig:
    """Connection strings for the Supabase Postgres instance.

    ``url`` is the transaction-pooler DSN (Supavisor :6543); ``direct_url`` is the
    session-mode DSN (:5432) used by migrations, LISTEN/NOTIFY, and tests.
    """

    url: str
    direct_url: str

    @classmethod
    def from_env(cls) -> DbConfig:
        url = os.environ.get(_POOLED_ENV)
        direct_url = os.environ.get(_DIRECT_ENV)
        missing = [name for name, val in ((_POOLED_ENV, url), (_DIRECT_ENV, direct_url)) if not val]
        if missing:
            raise ValidationError(
                f"Missing required database environment variable(s): {', '.join(missing)}"
            )
        assert url is not None
        assert direct_url is not None
        return cls(url=url, direct_url=direct_url)


__all__ = ["DbConfig"]
