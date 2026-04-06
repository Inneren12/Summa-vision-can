"""Shared fixtures for job runner tests."""

import pytest
from src.services.jobs.handlers import HANDLER_REGISTRY
from src.schemas.job_payloads import PAYLOAD_REGISTRY, CatalogSyncPayload


@pytest.fixture(autouse=True)
def _clean_registries():
    """Clean handler and payload registries between tests.

    Adds test-only job types to PAYLOAD_REGISTRY for the duration
    of each test, then removes them. Production registry stays clean.
    """
    saved_handlers = dict(HANDLER_REGISTRY)
    saved_payloads = dict(PAYLOAD_REGISTRY)

    # Register test-only payload types
    test_types = [
        "retry_test",
        "perm_test",
        "transient_test",
        "test",
        "audit_success_test",
        "audit_fail_test",
    ]

    from src.schemas.job_payloads import CatalogSyncPayload
    for t in test_types:
        PAYLOAD_REGISTRY[t] = CatalogSyncPayload

    yield

    HANDLER_REGISTRY.clear()
    HANDLER_REGISTRY.update(saved_handlers)
    PAYLOAD_REGISTRY.clear()
    PAYLOAD_REGISTRY.update(saved_payloads)
