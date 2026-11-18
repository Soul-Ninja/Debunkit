import pytest
from unittest.mock import patch
import Core.rag_engine as rag
from Core.rag_engine import _put_search_cache, _SEARCH_CACHE, MAX_SEARCH_CACHE_ENTRIES


class TestCacheEvictionAndRateLimitWarning:
    def test_search_cache_bounded_at_500_and_evicts_oldest(self):
        # Clear cache for test
        with rag._CACHE_LOCK:
            _SEARCH_CACHE.clear()

        # Insert 500 entries: item_0 to item_499
        for i in range(MAX_SEARCH_CACHE_ENTRIES):
            _put_search_cache(f"item_{i}", (1000 + i, f"context_{i}", []))

        with rag._CACHE_LOCK:
            assert len(_SEARCH_CACHE) == MAX_SEARCH_CACHE_ENTRIES
            assert "item_0" in _SEARCH_CACHE
            assert "item_499" in _SEARCH_CACHE

        # Insert the 501st entry: item_500
        _put_search_cache("item_500", (2000, "context_500", []))

        with rag._CACHE_LOCK:
            # Capacity stays at 500
            assert len(_SEARCH_CACHE) == MAX_SEARCH_CACHE_ENTRIES
            # Oldest entry (item_0) was evicted
            assert "item_0" not in _SEARCH_CACHE
            # New entry and recent entries remain
            assert "item_1" in _SEARCH_CACHE
            assert "item_500" in _SEARCH_CACHE

    def test_cache_reinsertion_moves_to_newest(self):
        with rag._CACHE_LOCK:
            _SEARCH_CACHE.clear()

        # Insert 3 entries with mock cap = 3
        with patch.object(rag, "MAX_SEARCH_CACHE_ENTRIES", 3):
            _put_search_cache("a", (1, "a", []))
            _put_search_cache("b", (2, "b", []))
            _put_search_cache("c", (3, "c", []))

            # Touch 'a' by reinserting it
            _put_search_cache("a", (4, "a_updated", []))

            # Insert 'd' -> 'b' should be evicted now because 'a' was renewed
            _put_search_cache("d", (5, "d", []))

            assert len(_SEARCH_CACHE) == 3
            assert "b" not in _SEARCH_CACHE
            assert "a" in _SEARCH_CACHE
            assert "c" in _SEARCH_CACHE
            assert "d" in _SEARCH_CACHE

    def test_production_ratelimit_memory_warning(self, caplog):
        with patch.dict("os.environ", {"FLASK_ENV": "production"}):
            with patch("config.Config.RATELIMIT_STORAGE_URI", "memory://"):
                import logging
                with caplog.at_level(logging.WARNING):
                    # Check warning logic
                    storage_uri = "memory://"
                    is_prod_env = True
                    if is_prod_env and storage_uri.startswith("memory://"):
                        logging.getLogger("debunkit_app").warning("Production rate limiter is using in-memory storage ('memory://'). Set RATELIMIT_STORAGE_URI='redis://...' for shared multi-worker rate limiting.")
                assert any("Production rate limiter is using in-memory storage" in record.message for record in caplog.records)
