"""Tests for ``LLMCache``.

Covers:
    * Cache key determinism (pure function — ARCH-PURA-001).
    * Cache hit / miss / TTL expiry.
    * Same prompt + different data_hash → different keys.
    * ``clear()`` empties the cache.
"""

from __future__ import annotations

import hashlib

from cachetools import TTLCache

from src.services.ai.llm_cache import LLMCache


# ---------------------------------------------------------------------------
# build_key
# ---------------------------------------------------------------------------


class TestBuildKey:
    """Tests for ``LLMCache.build_key``."""

    def test_deterministic(self) -> None:
        """Same inputs should always produce the same key."""
        key_a = LLMCache.build_key("hello", "data1")
        key_b = LLMCache.build_key("hello", "data1")
        assert key_a == key_b

    def test_format(self) -> None:
        """Key should be ``sha256(prompt) + '_' + sha256(data_hash)``."""
        prompt = "test prompt"
        data_hash = "cube-123"

        expected_prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()
        expected_data_hash = hashlib.sha256(data_hash.encode()).hexdigest()
        expected = f"{expected_prompt_hash}_{expected_data_hash}"

        assert LLMCache.build_key(prompt, data_hash) == expected

    def test_different_data_hash_different_key(self) -> None:
        """Same prompt, different data_hash → different cache key."""
        key_a = LLMCache.build_key("prompt", "hash-v1")
        key_b = LLMCache.build_key("prompt", "hash-v2")
        assert key_a != key_b

    def test_different_prompt_different_key(self) -> None:
        """Different prompt, same data_hash → different cache key."""
        key_a = LLMCache.build_key("prompt-A", "data")
        key_b = LLMCache.build_key("prompt-B", "data")
        assert key_a != key_b

    def test_empty_data_hash(self) -> None:
        """Empty data_hash should produce a valid key (hash of empty str)."""
        key = LLMCache.build_key("prompt", "")
        assert "_" in key
        parts = key.split("_")
        assert len(parts) == 2
        assert all(len(p) == 64 for p in parts)  # SHA-256 hex length


# ---------------------------------------------------------------------------
# Cache operations
# ---------------------------------------------------------------------------


class TestCacheOperations:
    """Tests for get / set / clear / size."""

    def test_get_miss(self) -> None:
        """Missing key should return ``None``."""
        cache = LLMCache(ttl_seconds=300)
        assert cache.get("nonexistent") is None

    def test_set_and_get(self) -> None:
        """Stored value should be retrievable."""
        cache = LLMCache(ttl_seconds=300)
        cache.set("key-1", "value-1")
        assert cache.get("key-1") == "value-1"

    def test_overwrite(self) -> None:
        """Setting a key twice should overwrite the first value."""
        cache = LLMCache(ttl_seconds=300)
        cache.set("key-1", "old")
        cache.set("key-1", "new")
        assert cache.get("key-1") == "new"

    def test_clear(self) -> None:
        """``clear()`` should remove all entries."""
        cache = LLMCache(ttl_seconds=300)
        cache.set("a", "1")
        cache.set("b", "2")
        assert cache.size == 2

        cache.clear()
        assert cache.size == 0
        assert cache.get("a") is None

    def test_size(self) -> None:
        """Size should track number of entries."""
        cache = LLMCache(ttl_seconds=300)
        assert cache.size == 0
        cache.set("x", "y")
        assert cache.size == 1


# ---------------------------------------------------------------------------
# TTL expiry
# ---------------------------------------------------------------------------


class TestTTLExpiry:
    """TTL-based expiry tests."""

    def test_expired_entry_returns_none(self) -> None:
        """Entries should disappear after TTL elapses."""
        import time as _time

        # cachetools.TTLCache.timer is read-only, so we inject a
        # custom timer at construction via the `timer` kwarg.
        offset: list[float] = [0.0]

        def fake_timer() -> float:
            return _time.monotonic() + offset[0]

        cache = LLMCache(ttl_seconds=10, max_size=128)
        # Replace internal store with one using our custom timer
        cache._store = TTLCache(maxsize=128, ttl=10, timer=fake_timer)

        cache.set("key", "value")
        assert cache.get("key") == "value"

        # Advance fake time past TTL
        offset[0] = 15.0
        assert cache.get("key") is None


# ---------------------------------------------------------------------------
# Max-size eviction
# ---------------------------------------------------------------------------


class TestMaxSizeEviction:
    """Max-size eviction tests."""

    def test_eviction_on_overflow(self) -> None:
        """Exceeding max_size should evict the oldest entry (LRU)."""
        cache = LLMCache(ttl_seconds=300, max_size=2)
        cache.set("a", "1")
        cache.set("b", "2")
        cache.set("c", "3")  # should evict "a"

        assert cache.get("a") is None
        assert cache.get("b") == "2"
        assert cache.get("c") == "3"
