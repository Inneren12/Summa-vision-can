"""Repository package for the Summa Vision persistence layer.

Re-exports all repository classes for convenient imports::

    from src.repositories import (
        PublicationRepository,
        LeadRepository,
    )
"""

from src.repositories.cube_catalog_repository import CubeCatalogRepository
from src.repositories.job_repository import JobRepository
from src.repositories.lead_repository import LeadRepository
from src.repositories.publication_repository import PublicationRepository

__all__ = [
    "CubeCatalogRepository",
    "JobRepository",
    "LeadRepository",
    "PublicationRepository",
]
