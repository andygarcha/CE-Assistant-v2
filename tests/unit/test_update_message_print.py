import logging
from unittest.mock import patch

from web_scraper.scraper import UpdateMessageForScraperProcess


def _embed_update() -> UpdateMessageForScraperProcess:
    return UpdateMessageForScraperProcess(
        is_embed=True, title="Test Title", description="Test description."
    )


def _text_update() -> UpdateMessageForScraperProcess:
    return UpdateMessageForScraperProcess(is_embed=False, text="Test text update.")


class TestPrintOutputsToConsole:
    def test_embed_update_prints_title_and_description(self):
        with patch("builtins.print") as mock_print:
            _embed_update().print()
        printed = mock_print.call_args[0][0]
        assert "Test Title" in printed
        assert "Test description." in printed

    def test_text_update_prints_text(self):
        with patch("builtins.print") as mock_print:
            _text_update().print()
        printed = mock_print.call_args[0][0]
        assert "Test text update." in printed


class TestPrintLoggingLevels:
    def test_full_and_info_logs_at_info_full_message(self, caplog):
        with caplog.at_level(logging.INFO, logger="web_scraper.scraper"):
            _text_update().print(full=True, info=True)
        assert any("Test text update." in r.message for r in caplog.records)
        assert all(r.levelno == logging.INFO for r in caplog.records)

    def test_full_only_logs_at_debug(self, caplog):
        with caplog.at_level(logging.DEBUG, logger="web_scraper.scraper"):
            _text_update().print(full=True, info=False)
        assert any("Test text update." in r.message for r in caplog.records)
        assert all(r.levelno == logging.DEBUG for r in caplog.records)

    def test_info_only_logs_at_info_truncated(self, caplog):
        long_text = "x" * 200
        with caplog.at_level(logging.INFO, logger="web_scraper.scraper"):
            _text_update().print(full=False, info=True)
            UpdateMessageForScraperProcess(is_embed=False, text=long_text).print(
                full=False, info=True
            )
        truncated = [r for r in caplog.records if "x" * 200 not in r.message]
        assert truncated
        for record in caplog.records:
            assert len(record.message) <= 100

    def test_neither_full_nor_info_logs_at_debug_truncated(self, caplog):
        long_text = "y" * 200
        with caplog.at_level(logging.DEBUG, logger="web_scraper.scraper"):
            UpdateMessageForScraperProcess(is_embed=False, text=long_text).print(
                full=False, info=False
            )
        assert caplog.records
        for record in caplog.records:
            assert len(record.message) <= 100
            assert record.levelno == logging.DEBUG
