"""add slug to publications

Revision ID: 77889c0ea7e3
Revises: a7d6b03efabf
Create Date: 2026-04-30 12:00:00.000000

Phase 2.2.0.5 backend slug infrastructure — Part 1.
Adds nullable slug column and backfills existing rows.

NOT NULL + UNIQUE enforcement is deferred to a later migration that
runs after write-path PRs deploy slug population. This expand-contract
sequencing prevents production INSERT failures during the rolling
deploy window.

OPS NOTE: once slug URLs are public-facing, do not downgrade this
migration in production; down->up can change slug paths and break links.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from slugify import slugify


# revision identifiers, used by Alembic.
revision: str = "77889c0ea7e3"
down_revision: Union[str, Sequence[str], None] = "a7d6b03efabf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


MAX_SLUG_LEN = 196
MIN_SLUG_BODY_LEN = 3
RESERVED_SLUGS: frozenset[str] = frozenset({
    "_next", "static", "api", "_error", "404", "500",
    "admin", "p", "about", "privacy", "terms", "login", "signup", "logout",
    "health", "robots", "sitemap", "favicon",
    "summa", "summa-vision",
    "search", "feed", "rss", "atom",
})


def upgrade() -> None:
    """Upgrade schema."""
    # Step 1: add nullable column (batch_alter_table for SQLite portability).
    # Column stays nullable in this migration; a later migration will
    # enforce NOT NULL + UNIQUE once write-path PRs (Chunks 2-4) ship.
    with op.batch_alter_table("publications", schema=None) as batch_op:
        batch_op.add_column(sa.Column("slug", sa.String(length=200), nullable=True))

    # Step 2: backfill slugs via Python loop (slugify + collision suffixing
    # cannot be expressed in pure SQL).
    _backfill_slugs()


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("publications", schema=None) as batch_op:
        batch_op.drop_column("slug")


def _backfill_slugs() -> None:
    """Walk publications by id ASC. Slugify the headline; if empty/short or
    collides with already-assigned/reserved slugs, suffix ``-2, -3, ...``
    unboundedly until a free slot is found. Empty/short fallback uses
    ``publication-{id}``.

    Backfill operates on a fixed snapshot of existing rows, so the suffix
    loop is unbounded — capping it (the runtime ``generate_slug`` uses 99
    for operator UX) could abort a deployment on a legitimately
    collision-heavy dataset.

    Constants are duplicated from runtime intentionally per Alembic
    immutability convention: a migration must keep producing the same
    output even if runtime constants drift.
    """
    bind = op.get_bind()
    rows = bind.execute(
        sa.text("SELECT id, headline FROM publications ORDER BY id ASC")
    ).fetchall()

    assigned: set[str] = set()
    for row in rows:
        slug = _generate_slug_for_backfill(row.id, row.headline, assigned)
        assigned.add(slug)
        bind.execute(
            sa.text("UPDATE publications SET slug = :s WHERE id = :i"),
            {"s": slug, "i": row.id},
        )


def _generate_slug_for_backfill(
    pub_id: int, headline: str | None, assigned: set[str]
) -> str:
    base = slugify(headline or "", max_length=MAX_SLUG_LEN)
    if not base or len(base) < MIN_SLUG_BODY_LEN:
        return f"publication-{pub_id}"

    blocked = assigned | RESERVED_SLUGS
    if base not in blocked:
        return base

    n = 2
    while True:
        candidate = f"{base}-{n}"
        if candidate not in blocked:
            return candidate
        n += 1
