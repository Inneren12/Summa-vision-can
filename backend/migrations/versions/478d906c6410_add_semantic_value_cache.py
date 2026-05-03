"""add semantic_value_cache table

Phase 3.1aaa: persistent cache of StatCan vectorDataPoint rows keyed by
(cube_id, semantic_key, coord, ref_period). Populated best-effort on
mapping save (auto-prime) and refreshed nightly by the
``statcan_value_cache_refresh`` scheduler job. See
``docs/recon/phase-3-1aaa.md`` for the full design.

Postgres-only DDL: the ``period_start`` column is a STORED GENERATED
column whose expression invokes ``parse_ref_period_to_date``, a
PL/pgSQL function created in this migration. SQLite test fixtures
bypass migrations and instantiate the schema via ``Base.metadata.
create_all`` — the ORM declares ``period_start`` as a regular Date
column there (parity is intentional: the GENERATED clause is enforced
in the live database only).

Revision ID: 478d906c6410
Revises: a1b2c3d4e5f6
Create Date: 2026-05-03
"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "478d906c6410"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        # SQLite fixtures use Base.metadata.create_all; the GENERATED
        # column + plpgsql function are PG-only.
        return

    # 1. Idempotent ref_period parser. Used by the GENERATED column.
    op.execute(
        r"""
CREATE OR REPLACE FUNCTION parse_ref_period_to_date(period TEXT)
RETURNS DATE AS $$
DECLARE
  y INT;
  m INT;
  q INT;
BEGIN
  IF period ~ '^\d{4}-\d{2}-\d{2}$' THEN
    RETURN period::date;
  ELSIF period ~ '^\d{4}-\d{2}$' THEN
    y := substring(period from 1 for 4)::int;
    m := substring(period from 6 for 2)::int;
    RETURN make_date(y, m, 1);
  ELSIF period ~ '^\d{4}-Q[1-4]$' THEN
    y := substring(period from 1 for 4)::int;
    q := substring(period from 7 for 1)::int;
    RETURN make_date(y, ((q - 1) * 3) + 1, 1);
  ELSIF period ~ '^\d{4}$' THEN
    y := period::int;
    RETURN make_date(y, 1, 1);
  ELSE
    -- Phase 3.1aaa FIX-R1 (Blocker 3): tolerant fallback. Unknown
    -- ref_period formats produce ``period_start = NULL`` rather than
    -- aborting the row insert. Cache layer must remain tolerant of
    -- StatCan format drift (Q-impl-3); resolve/sort fallbacks for
    -- NULL period_start are a downstream concern.
    RETURN NULL;
  END IF;
END;
$$ LANGUAGE plpgsql IMMUTABLE;
        """
    )

    # 2. Table.
    op.execute(
        """
CREATE TABLE semantic_value_cache (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    cube_id VARCHAR(50) NOT NULL,
    product_id BIGINT NOT NULL,
    semantic_key VARCHAR(100) NOT NULL,
    coord VARCHAR(50) NOT NULL,
    ref_period VARCHAR(20) NOT NULL,
    period_start DATE GENERATED ALWAYS AS (parse_ref_period_to_date(ref_period)) STORED,
    value NUMERIC(18, 6),
    missing BOOLEAN NOT NULL DEFAULT FALSE,
    decimals INTEGER NOT NULL DEFAULT 0,
    scalar_factor_code INTEGER NOT NULL DEFAULT 0,
    symbol_code INTEGER NOT NULL DEFAULT 0,
    security_level_code INTEGER NOT NULL DEFAULT 0,
    status_code INTEGER NOT NULL DEFAULT 0,
    frequency_code INTEGER,
    vector_id BIGINT,
    response_status_code INTEGER,
    source_hash VARCHAR(64) NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL,
    release_time TIMESTAMPTZ,
    is_stale BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_semantic_value_cache_mapping
      FOREIGN KEY (cube_id, semantic_key)
      REFERENCES semantic_mappings (cube_id, semantic_key)
      ON DELETE CASCADE,
    CONSTRAINT uq_semantic_value_cache_lookup
      UNIQUE (cube_id, semantic_key, coord, ref_period)
);
        """
    )

    # 3. Indexes.
    op.execute(
        "CREATE INDEX ix_semantic_value_cache_product_id "
        "ON semantic_value_cache (product_id);"
    )
    op.execute(
        "CREATE INDEX ix_semantic_value_cache_coord "
        "ON semantic_value_cache (cube_id, semantic_key, coord);"
    )
    op.execute(
        "CREATE INDEX ix_semantic_value_cache_fetched_at "
        "ON semantic_value_cache (fetched_at);"
    )
    op.execute(
        "CREATE INDEX ix_semantic_value_cache_period_start "
        "ON semantic_value_cache (period_start);"
    )
    op.execute(
        "CREATE INDEX ix_semantic_value_cache_is_stale "
        "ON semantic_value_cache (is_stale) WHERE is_stale = true;"
    )

    # 4. semantic_mappings (cube_id, semantic_key) must be a unique
    #    constraint for the FK to bind. The 3.1a migration already
    #    created uq_semantic_mappings_cube_key on those exact columns,
    #    so no extra DDL is required here. (table_args parity check.)


def downgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return

    op.execute("DROP TABLE IF EXISTS semantic_value_cache;")
    op.execute("DROP FUNCTION IF EXISTS parse_ref_period_to_date(TEXT);")
