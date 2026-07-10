"""Tests for scraper.py functions that are currently unimplemented stubs.

These exist so a future implementation of either function is forced to
update (not silently pass) these tests, and so the stub state itself is
covered rather than untested dead code.
"""

import pytest

from web_scraper.scraper import check_curator_steam, database_reload


class TestCheckCuratorSteam:
    def test_returns_none(self):
        # TODO in scraper.py: unimplemented, currently a no-op.
        assert check_curator_steam() is None


class TestDatabaseReload:
    def test_raises_not_implemented(self):
        with pytest.raises(NotImplementedError):
            database_reload()
