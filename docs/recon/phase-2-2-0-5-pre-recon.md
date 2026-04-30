# Phase 2.2.0.5 Pre-Recon — Backend slug Infrastructure

**Status:** Pre-recon (read-only inventory) — IN PROGRESS  
**Author:** Claude Code (architect agent)  
**Date:** 2026-04-30  
**Branch:** claude/phase-2-2-0-5-pre-recon  
**Origin:** Phase 2.2 recon-proper Chunk B §B5 (Q-impl-2.2-1 SLUG-C escalation)  
**Founder lock-in:** Q-2.2-9 (2026-04-30) backend-owned slug column

## Context

Phase 2.2 frontend distribution kit needs `${PUBLIC_SITE_URL}/p/${slug}`. SLUG-C inventory in Chunk B confirmed: no `slug` or `public_url` on PublicationResponse. Founder decided slug is backend-owned column, analogous to Phase 2.2.0 lineage_key model.

This pre-recon is read-only inventory of existing code state. Recon-proper designs the column shape, generator, migration, and schema changes. Impl phase ships them.

**Recon chunks (planned):**
- Recon-proper Chunk A: column shape + generator algorithm + edge cases
- Recon-proper Chunk B: migration design + backfill strategy
- Recon-proper Chunk C: schema + service callers + immutability enforcement
- Recon-proper Chunk D: test strategy + DEBT entries + Phase 2.2 unblock

## A. Existing Publication model + schema inventory

### A1. Publication ORM model

`$ grep -n "Column\|relationship\|UniqueConstraint\|Index\|__tablename__" backend/src/models/publication.py`
```text
14:from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, Text, UniqueConstraint, func
70:    __tablename__ = "publications"
72:        UniqueConstraint(
```

`$ nl -ba backend/src/models/publication.py | sed -n '70,162p'`
```text
70    __tablename__ = "publications"
71    __table_args__ = (
72        UniqueConstraint(
73            "source_product_id",
74            "config_hash",
75            "version",
76            name="uq_publication_lineage_version",
77        ),
78    )
80    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
81    headline: Mapped[str] = mapped_column(String(500), nullable=False)
82    chart_type: Mapped[str] = mapped_column(String(100), nullable=False)
83    s3_key_lowres: Mapped[str | None] = mapped_column(Text, nullable=True)
84    s3_key_highres: Mapped[str | None] = mapped_column(Text, nullable=True)
85    virality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
86    source_product_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
87    version: Mapped[int] = mapped_column(nullable=False, default=1, server_default="1")
88    config_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
89    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
90    cloned_from_publication_id: Mapped[int | None] = mapped_column(
91        ForeignKey("publications.id", ondelete="SET NULL"),
92        nullable=True,
93        index=True,
94    )
95    lineage_key: Mapped[str] = mapped_column(
96        String(length=36),
97        nullable=False,
98        index=True,
99        doc="UUID v7 lineage identifier; clones share with source",
100    )
101    status: Mapped[PublicationStatus] = mapped_column(
102        Enum(PublicationStatus, name="publication_status"),
103        nullable=False,
104        default=PublicationStatus.DRAFT,
105        server_default="DRAFT",
106        index=True,
107    )
108    created_at: Mapped[datetime] = mapped_column(
109        DateTime(timezone=True),
110        nullable=False,
111        default=lambda: datetime.now(timezone.utc),
112        index=True,
113    )
119    eyebrow: Mapped[str | None] = mapped_column(String(255), nullable=True)
120    description: Mapped[str | None] = mapped_column(Text, nullable=True)
121    source_text: Mapped[str | None] = mapped_column(String(500), nullable=True)
122    footnote: Mapped[str | None] = mapped_column(Text, nullable=True)
128    visual_config: Mapped[str | None] = mapped_column(Text, nullable=True)
138    review: Mapped[str | None] = mapped_column(Text, nullable=True)
148    document_state: Mapped[str | None] = mapped_column(Text, nullable=True)
153    updated_at: Mapped[datetime | None] = mapped_column(
154        DateTime(timezone=True),
155        nullable=True,
156        onupdate=func.now(),
157    )
158    published_at: Mapped[datetime | None] = mapped_column(
159        DateTime(timezone=True),
160        nullable=True,
161    )
```

Key fields relevant to slug work: `id`, `headline`, `lineage_key`, `cloned_from_publication_id` are present; `slug` is absent.

### A2. Schema classes

`$ grep -n "^class " backend/src/schemas/publication.py`
```text
42:class BrandingConfig(BaseModel):
60:class VisualConfig(BaseModel):
96:class ReviewPayload(BaseModel):
128:class PublicationCreate(BaseModel):
161:class PublicationUpdate(BaseModel):
205:class PublicationResponse(BaseModel):
277:class PublicationPublicResponse(BaseModel):
```

`$ grep -n "headline" backend/src/schemas/publication.py | head -10`
```text
131:    All fields except ``headline`` and ``chart_type`` are optional.
144:    headline: str = Field(..., min_length=1, max_length=500)
182:    headline: Optional[str] = Field(None, min_length=1, max_length=500)
214:        headline: Short title for the graphic.
234:    headline: str
290:    headline: str
```

`$ grep -n -A 20 "class PublicationUpdate" backend/src/schemas/publication.py`
```text
161:class PublicationUpdate(BaseModel):
180-    model_config = ConfigDict(extra="forbid")
```

Inventory finding: PublicationUpdate is an explicit class with its own field declarations and `extra="forbid"` (not an inheritance alias that auto-copies all create fields).

### A3. Existing Settings.public_site_url state

`$ grep -n "public_site_url\|PUBLIC_SITE_URL" backend/src/core/config.py`
```text
129:    public_site_url: str = "http://localhost:3000"  # Prod: https://summa.vision
156:            if not self.public_site_url:
157:                errors.append("PUBLIC_SITE_URL is required in production")
```

## B. Existing services/publications/ structure

`$ ls -la backend/src/services/publications/`
```text
total 28
drwxr-xr-x  2 root root 4096 Apr 30 01:00 .
drwxr-xr-x 16 root root 4096 Apr 30 01:00 ..
-rw-r--r--  1 root root    0 Apr 30 01:00 __init__.py
-rw-r--r--  1 root root 2667 Apr 30 01:00 clone.py
-rw-r--r--  1 root root 1732 Apr 30 01:00 etag.py
-rw-r--r--  1 root root 3324 Apr 30 01:00 exceptions.py
-rw-r--r--  1 root root 5115 Apr 30 01:00 lineage.py
```

`$ grep -rn "^def \|^async def \|^class " backend/src/services/publications/ | head -20`
```text
backend/src/services/publications/exceptions.py:16:class PublicationApiError(HTTPException):
backend/src/services/publications/exceptions.py:36:class PublicationNotFoundError(PublicationApiError):
backend/src/services/publications/exceptions.py:44:class PublicationUpdatePayloadInvalidError(PublicationApiError):
backend/src/services/publications/exceptions.py:52:class PublicationInternalSerializationError(PublicationApiError):
backend/src/services/publications/exceptions.py:60:class PublicationCloneNotAllowedError(PublicationApiError):
backend/src/services/publications/exceptions.py:74:class PublicationPreconditionFailedError(PublicationApiError):
backend/src/services/publications/lineage.py:37:def compute_config_hash(
backend/src/services/publications/lineage.py:53:def derive_size_from_visual_config(
backend/src/services/publications/lineage.py:129:def generate_lineage_key() -> str:
backend/src/services/publications/lineage.py:145:def derive_clone_lineage_key(source: "Publication") -> str:
backend/src/services/publications/clone.py:26:async def clone_publication(*, session: AsyncSession, source_id: int) -> Publication:
backend/src/services/publications/etag.py:14:def compute_etag(pub: Publication) -> str:
```

### B1. lineage.py reference

`$ cat backend/src/services/publications/lineage.py | head -50`
```text
"""Lineage helpers for Publication R19 versioning.

Pure functions per ARCH-PURA-001. No DB access here.
"""
...
try:
    from uuid import uuid7
except ImportError:
    from uuid_utils import uuid7
```

### B2. Existing slugify libraries in pyproject.toml

`$ grep -E "slugify|unidecode|transliterat" backend/pyproject.toml`
```text
(no matches)
```

## C. Existing migrations + alembic state

`$ ls backend/migrations/versions/ | tail -10`
```text
a1c3f7d82e09_add_category_to_lead.py
a3e81c0f5d21_add_document_state_to_publication.py
a7d6b03efabf_add_lineage_key_to_publications.py
ab79f3662ba3_add_indexes.py
b4f9a21c8d77_add_cloned_from_to_publication.py
c4d8e1f23a01_drop_llm_requests_table.py
d7a1b2c3e4f5_add_subject_key_to_jobs.py
e9b4f8a72c10_add_editorial_and_visual_config_to_publication.py
f2a7d9c3b481_add_review_to_publication.py
ffbd7002559e_add_jobs_table.py
```

`$ (cd backend && alembic heads)`
```text
a7d6b03efabf (head)
```

### C1. Phase 2.2.0 migration as reference

`$ grep -l "lineage_key" backend/migrations/versions/*.py`
```text
backend/migrations/versions/a7d6b03efabf_add_lineage_key_to_publications.py
```

`$ cat backend/migrations/versions/a7d6b03efabf_add_lineage_key_to_publications.py | head -80`
```text
... Adds nullable column, backfills existing rows ... then enforces NOT NULL + adds index ...
```

### C2. Existing publications table indices/constraints

`$ grep -n "Index\|UniqueConstraint" backend/src/models/publication.py`
```text
14:from sqlalchemy import ... UniqueConstraint, func
72:        UniqueConstraint(
```

## D. Service callers — where slug generation invoked

### D1. Publication construction sites

`$ rg -n "Publication\(" backend/src | head -20`
```text
backend/src/models/publication.py:27:class Publication(Base):
backend/src/models/publication.py:165:            f"<Publication(id={self.id}, headline={self.headline!r}, "
backend/src/repositories/publication_repository.py:116:                publication = Publication(
backend/src/repositories/publication_repository.py:167:        publication = Publication(
backend/src/repositories/publication_repository.py:204:        clone = Publication(
backend/src/repositories/publication_repository.py:469:        publication = Publication(**payload)
```

### D2. Service-layer invocation patterns

`$ grep -rn "create_full\|create_clone" backend/src/api/routers/ backend/src/services/ | head -10`
```text
backend/src/api/routers/admin_publications.py:269:    publication = await repo.create_full(data)
backend/src/services/publications/clone.py:62:            clone = await repo.create_clone(
```

### D3. Headline source verification

`$ grep -n "headline" backend/src/services/publications/clone.py 2>/dev/null | head -5`
```text
41:    new_headline = source.headline if source.headline.startswith(_COPY_PREFIX) else f"{_COPY_PREFIX}{source.headline}"
47:        title=new_headline,
64:                new_headline=new_headline,
```

## E. Test fixtures + Publication() callsites

### E1. Factory state

`$ grep -n "make_publication\|def make_publication" backend/tests/conftest.py`
```text
82:def make_publication(**overrides: Any) -> Publication:
```

### E2. Direct Publication() callsites in tests

`$ grep -rn "Publication(" backend/tests/ | grep -v "make_publication" | grep -v "_FakePublication\|PublicationResponse\|PublicationCreate"`
```text
backend/tests/conftest.py:101:    return Publication(**defaults)
```

## F. Open questions for recon-proper

### F1. Q-2.2.0.5-1 — slug column nullability transition strategy
Pre-recon recommendation: (a) single migration bundle (nullable -> backfill -> NOT NULL + unique).

### F2. Q-2.2.0.5-2 — slugify library choice
Pre-recon recommendation: (a) `python-slugify`.

### F3. Q-2.2.0.5-3 — collision handling specifics
Pre-recon recommendation: (a) incremental suffix (`-2`, `-3`, ...) up to 99 attempts.

### F4. Q-2.2.0.5-4 — non-Latin headline handling
Pre-recon recommendation: (a) transliteration.

### F5. Q-2.2.0.5-5 — empty/short headline guard
Pre-recon recommendation: (a) schema-level rejection.

### F6. Q-2.2.0.5-6 — reserved slug paths
Pre-recon recommendation: hardcoded blacklist + disambiguation path.

### F7. Q-2.2.0.5-7 — backfill strategy for existing publications
Pre-recon recommendation: (b) Python-loop backfill mirroring runtime slug generation logic.

### F8. Q-2.2.0.5-8 — make_publication factory update
Pre-recon recommendation: (a) auto-default slug in factory.

### F9. Q-2.2.0.5-9 — PublicationUpdate slug exclusion verification
Inventory finding: `PublicationUpdate` is explicit class body with `extra="forbid"`; slug exclusion can be controlled directly at schema field list.

## G. DEBT and roadmap touchpoints

### G1. Existing DEBT entries touching slug work

`$ grep -n -i "slug\|url path\|public path" DEBT.md | head -10`
```text
(no matches)
```

### G2. ROADMAP_DEPENDENCIES.md — Phase 2.2.0.5 row presence

`$ grep -n "2.2.0.5\|2\.2\.0\.5" docs/architecture/ROADMAP_DEPENDENCIES.md`
```text
(no matches)
```

### G3. Phase 2.2 dependency chain touchpoint
Current recorded chain in docs (pre-change) remains without explicit 2.2.0.5 entry.

## H. Pre-recon summary

1. Inventory completed for Publication ORM and publication schemas.
2. Inventory completed for `services/publications` structure and lineage reference patterns.
3. Migration baseline confirmed with single Alembic head and lineage migration reference.
4. Publication construction and caller sites inventoried.
5. Test fixture/factory footprint inventoried.
6. Open questions enumerated as Q-2.2.0.5-1 through Q-2.2.0.5-9.
7. DEBT/roadmap touchpoints checked for current slug references.

No code changes were made in this pre-recon phase; output is inventory-only documentation.
