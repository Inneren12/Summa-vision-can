'use client';

import React, { useMemo, useState } from 'react';
import type { BarItem } from '../../types';
import { TK } from '../../config/tokens';
import { makeId } from '../../utils/ids';

interface BarItemsEditorProps {
  items: BarItem[];
  onChange: (items: BarItem[]) => void;
  // canEditValues: user can change label/value/flag/highlight of existing items
  canEditValues: boolean;
  // canEditStructure: user can add new items or remove existing ones
  canEditStructure: boolean;
}

export function BarItemsEditor({ items, onChange, canEditValues, canEditStructure }: BarItemsEditorProps) {
  // Backfill _id for items loaded from legacy docs that lack one. Drafts key
  // off _id so mid-edit state survives row removal/reorder (index-keyed
  // drafts would stick to the wrong row after mutation).
  const itemsWithIds = useMemo(
    () => items.map(it => (it._id ? it : { ...it, _id: makeId() })),
    [items],
  );

  const [drafts, setDrafts] = useState<Record<string, string>>({});

  const upd = <K extends keyof BarItem>(idx: number, key: K, val: BarItem[K]) => {
    const next = [...itemsWithIds];
    next[idx] = { ...next[idx], [key]: val };
    onChange(next);
  };
  const del = (idx: number) => onChange(itemsWithIds.filter((_, i) => i !== idx));
  const add = () => onChange([...itemsWithIds, { label: "New", value: 0, flag: "", highlight: false, _id: makeId() }]);

  const handleValueChange = (id: string, rawStr: string) => {
    setDrafts(prev => ({ ...prev, [`${id}_value`]: rawStr }));
    const parsed = parseFloat(rawStr);
    if (Number.isFinite(parsed)) {
      const idx = itemsWithIds.findIndex(it => it._id === id);
      if (idx >= 0) upd(idx, "value", parsed);
    }
  };

  const commitValueDraft = (id: string) => {
    setDrafts(prev => {
      const next = { ...prev };
      delete next[`${id}_value`];
      return next;
    });
  };

  const sty: React.CSSProperties = { fontSize: "9px", fontFamily: TK.font.data, background: TK.c.bgSurf, color: TK.c.txtP, border: `1px solid ${TK.c.brd}`, borderRadius: "2px", padding: "3px 5px", outline: "none", boxSizing: "border-box" };
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "3px" }}>
      <div style={{ fontSize: "8px", fontFamily: TK.font.data, color: TK.c.txtM, textTransform: "uppercase" }}>DATA ITEMS ({itemsWithIds.length})</div>
      <div style={{ maxHeight: "180px", overflowY: "auto" }}>
        {itemsWithIds.map((it, i) => (
          <div key={it._id} style={{ display: "flex", gap: "2px", alignItems: "center", marginBottom: "2px" }}>
            <input value={it.flag || ""} onChange={e => canEditValues && upd(i, "flag", e.target.value)} style={{ ...sty, width: "24px", textAlign: "center" }} disabled={!canEditValues} title="Flag" />
            <input value={it.label} onChange={e => canEditValues && upd(i, "label", e.target.value)} style={{ ...sty, flex: 1 }} disabled={!canEditValues} title="Label" />
            <input
              type="number"
              value={drafts[`${it._id}_value`] ?? String(it.value)}
              onChange={e => canEditValues && handleValueChange(it._id!, e.target.value)}
              onBlur={() => commitValueDraft(it._id!)}
              style={{ ...sty, width: "50px" }}
              disabled={!canEditValues}
              title="Value"
            />
            <button type="button" onClick={() => canEditValues && upd(i, "highlight", !it.highlight)} style={{ ...sty, background: it.highlight ? TK.c.acc + "30" : TK.c.bgSurf, color: it.highlight ? TK.c.acc : TK.c.txtM, cursor: canEditValues ? "pointer" : "default", width: "18px", textAlign: "center" }} disabled={!canEditValues} title="Highlight">{"\u2605"}</button>
            {/* Remove button — only in structural-edit mode (Design) */}
            {canEditStructure && <button type="button" onClick={() => del(i)} style={{ ...sty, color: TK.c.err, cursor: "pointer", width: "18px", textAlign: "center" }} title="Remove">{"\u00D7"}</button>}
          </div>
        ))}
      </div>
      {/* Add button — only in structural-edit mode (Design) */}
      {canEditStructure && <button type="button" onClick={add} style={{ fontSize: "8px", fontFamily: TK.font.data, background: TK.c.bgAct, color: TK.c.acc, border: `1px solid ${TK.c.brd}`, borderRadius: "2px", padding: "3px 8px", cursor: "pointer", width: "100%" }}>+ ADD ITEM</button>}
    </div>
  );
}
