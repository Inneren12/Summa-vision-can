## DEFERRED-E13: Stable _id for table_enriched rows and small_multiple items
- **Source:** PR #88 review iteration 8
- **Severity:** low
- **Description:** `normalizeBlockData()` synthesizes deterministic `_id` for bar_horizontal items, line_editorial series, and comparison_kpi items — the three block types with row-level draft-state editors. table_enriched rows and small_multiple items do NOT receive `_id` because their editors don't currently have per-row draft state. If row-level editing with draft state is added for these types in Stage 3+, they must be added to `normalizeBlockData()`.
