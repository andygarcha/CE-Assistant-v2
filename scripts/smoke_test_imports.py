"""
Import smoke test for the two real entrypoints: the Discord bot (main.py)
and the scraper process (scraper_main.py).

This exists to catch import-time errors -- circular imports, missing
modules, syntax errors -- that ruff/pyright/pytest can all miss. pytest in
particular never touches these files directly: `tests/conftest.py` patches
`LocalCache.rebuild_from_supabase` before any test module imports
`Modules.SupabaseReader`, so pytest never exercises the real import graph
these two entrypoints trigger.

main.py has no `if __name__ == "__main__":` guard -- it calls
`client.run(discord_token)` unconditionally at module level, so merely
importing it always tries to connect to Discord. `discord.Client.run` is
patched out below so this only exercises the import graph, not a real
connection. scraper_main.py does have a proper `__main__` guard.

Run with:  python scripts/smoke_test_imports.py
Requires a .env with at least SUPABASE_URL, SUPABASE_SECRET_KEY,
DISCORD_BOT_TOKEN, and DISCORD_GUILD_ID set (dummy values are fine -- no
network calls are made; LocalCache's Supabase sync is patched out below).
"""

import os
import sys
from unittest.mock import patch

# Ensure the repo root (this script's parent directory) is on sys.path, so
# `Modules`/`main`/`scraper_main` resolve regardless of the CWD this is run
# from.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

with (
    patch("Modules.LocalCache.rebuild_from_supabase", return_value=None),
    patch(
        "Modules.LocalCache.run_integrity_check",
        return_value={"synced": [], "removed": [], "schema": []},
    ),
    # main.py calls client.run(...) unconditionally at module level -- stub
    # it out so importing main.py doesn't try to actually connect to Discord.
    patch("discord.Client.run", return_value=None),
):
    try:
        import main  # noqa: F401
    except Exception:
        print("FAILED: main.py did not import cleanly.", file=sys.stderr)
        raise

    try:
        import scraper_main  # noqa: F401
    except Exception:
        print("FAILED: scraper_main.py did not import cleanly.", file=sys.stderr)
        raise

print("Smoke test passed: main.py and scraper_main.py both import cleanly.")
