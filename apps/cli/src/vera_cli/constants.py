"""Fixed identifiers shared across CLI commands (dev seed tenant + user).

These string literals must match ``supabase/seed.sql`` verbatim so that
``vera dev seed`` and the ``--tenant`` / ``--user`` defaults line up.
"""

from __future__ import annotations

# Must match supabase/seed.sql — see spec §8.
DEV_TENANT_ID = "0000000d-0000-4000-8000-000000000001"
DEV_USER_ID = "0000000d-0000-4000-8000-000000000002"

__all__ = ["DEV_TENANT_ID", "DEV_USER_ID"]
