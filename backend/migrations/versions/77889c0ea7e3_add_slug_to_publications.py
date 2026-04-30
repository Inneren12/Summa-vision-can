"""add slug to publications

Revision ID: 77889c0ea7e3
Revises: a7d6b03efabf
Create Date: 2026-04-30 12:00:00.000000

Phase 2.2.0.5 backend slug infrastructure. Adds nullable column,
backfills existing rows by slugifying headlines with collision suffixing,
then enforces NOT NULL + UNIQUE. Atomic within one revision so a
mid-backfill failure rolls cleanly.

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
    # Step 1: add nullable column (batch_alter_table for SQLite portability)
    with op.batch_alter_table("publications", schema=None) as batch_op:
        batch_op.add_column(sa.Column("slug", sa.String(length=200), nullable=True))

    # Step 2: backfill slugs via Python loop (slugify + collision suffixing
    # cannot be expressed in pure SQL).
    _backfill_slugs()

    # Step 3: enforce NOT NULL + UNIQUE after backfill. Wrapped in batch so
    # SQLite copy-and-move picks up both changes in one rebuild.
    with op.batch_alter_table("publications", schema=None) as batch_op:
        batch_op.alter_column(
            "slug",
            existing_type=sa.String(length=200),
            nullable=False,
        )
        batch_op.create_unique_constraint("uq_publications_slug", ["slug"])


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("publications", schema=None) as batch_op:
        batch_op.drop_constraint("uq_publications_slug", type_="unique")
        batch_op.drop_column("slug")


def _backfill_slugs() -> None:
    """Walk publications by id ASC. Slugify the headline; if empty/short or
    collides with already-assigned/reserved slugs, suffix ``-2..-99`` until
    a free slot is found. Empty/short fallback uses ``publication-{id}``.

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

    for n in range(2, 100):
        candidate = f"{base}-{n}"
        if candidate not in blocked:
            return candidate

    raise RuntimeError(
        f"Slug collision exhausted for id={pub_id}, "
        f"headline={headline!r}; manual intervention required."
    )
