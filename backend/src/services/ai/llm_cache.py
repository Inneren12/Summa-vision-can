"""LLM response cache with data-aware invalidation.

The cache key is ``sha256(prompt) + "_" + sha256(data_hash_string)``
so that a new StatCan release — even with the **same** prompt wording —
invalidates the cache automatically.

The TTL defaults to 24 hours and is backed by ``cachetools.TTLCache``
for in-memory, time-bounded expiry.

Architecture notes:
    * ``build_key`` is a **pure function** — no I/O, no side effects
      (ARCH-PURA-001).
    * ``LLMCache`` receives its TTL via constructor; it never reads
      env vars or settings internally.
"""

from __future__ import annotations

import hashlib

from cachetools import TTLCache


class LLMCache:
    """In-memory TTL cache for LLM responses.

    Attributes:
        _store: A ``TTLCache`` with configurable max size and TTL.
    """

    def __init__(
        self,
        *,
        ttl_seconds: int = 86_400,
        max_size: int = 1024,
    ) -> None:
        """Initialise the cache.

        Args:
            ttl_seconds: Time-to-live for each entry in seconds
                         (default: 86400 = 24 h).
            max_size: Maximum number of entries to keep.
        """
        self._store: TTLCache[str, str] = TTLCache(
            maxsize=max_size, ttl=ttl_seconds
        )

    # -- pure function (ARCH-PURA-001) -------------------------------------

    @staticmethod
    def build_key(prompt: str, data_hash: str) -> str:
        """Build a deterministic cache key from *prompt* and *data_hash*.

        Key format::

            sha256(prompt) + "_" + sha256(data_hash)

        If *data_hash* is empty, the second component is the hash of an
        empty string — cache invalidation still works correctly when a
        non-empty ``data_hash`` is supplied later.

        Args:
            prompt: The full prompt text.
            data_hash: A hash (or identifier) derived from the
                       underlying data (e.g. StatCan cube ID +
                       release timestamp, or DataFrame metadata).

        Returns:
            A deterministic string safe to use as a dict key.
        """
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()
        data_component = hashlib.sha256(data_hash.encode()).hexdigest()
        return f"{prompt_hash}_{data_component}"

    # -- standard cache operations -----------------------------------------

    def get(self, key: str) -> str | None:
        """Return the cached value or ``None`` on miss/expiry."""
        return self._store.get(key)

    def set(self, key: str, value: str) -> None:
        """Store *value* under *key* with the configured TTL."""
        self._store[key] = value

    def clear(self) -> None:
        """Remove all entries from the cache."""
        self._store.clear()

    @property
    def size(self) -> int:
        """Return the current number of entries in the cache."""
        return len(self._store)
