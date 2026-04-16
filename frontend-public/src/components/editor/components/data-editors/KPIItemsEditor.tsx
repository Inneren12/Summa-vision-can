'use client';

import React from 'react';
import type { Direction, KPIItem } from '../../types';
import { TK } from '../../config/tokens';
import { makeId } from '../../utils/ids';

interface KPIItemsEditorProps {
  items: KPIItem[];
  onChange: (items: KPIItem[]) => void;
  // canEditValues: change label/value/delta/direction of existing KPI
  canEditValues: boolean;
  // canEditStructure: add/remove KPIs
  canEditStructure: boolean;
}

export function KPIItemsEditor({ items, onChange, canEditValues, canEditStructure }: KPIItemsEditorProps) {
  const upd = <K extends keyof KPIItem>(idx: number, key: K, val: KPIItem[K]) => {
    const next = [...items];
    next[idx] = { ...next[idx], [key]: val };
    onChange(next);
  };

  const add = () => {
    if (!canEditStructure) return;
    onChange([
      ...items,
      {
        label: "New Metric",
        value: "0",
        delta: "",
        direction: "neutral" as Direction,
        _id: makeId(),
      },
    ]);
  };

  const remove = (idx: number) => {
    if (!canEditStructure) return;
    if (items.length <= 2) return; // KPI needs at least 2 items (matches guard)
    onChange(items.filter((_, i) => i !== idx));
  };

  const sty: React.CSSProperties = { fontSize: "9px", fontFamily: TK.font.data, background: TK.c.bgSurf, color: TK.c.txtP, border: `1px solid ${TK.c.brd}`, borderRadius: "2px", padding: "3px 5px", outline: "none", boxSizing: "border-box" };
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "3px" }}>
      <div style={{ fontSize: "8px", fontFamily: TK.font.data, color: TK.c.txtM, textTransform: "uppercase" }}>KPI CARDS ({items.length})</div>
      {items.map((it, i) => (
        <div key={it._id} style={{ padding: "4px", border: `1px solid ${TK.c.brd}`, borderRadius: "3px", marginBottom: "3px", position: "relative" }}>
          {/* Remove button — only in structural-edit mode (Design) */}
          {canEditStructure && items.length > 2 && (
            <button
              type="button"
              onClick={() => remove(i)}
              style={{
                position: "absolute",
                top: "2px",
                right: "2px",
                background: "none",
                border: 0,
                color: TK.c.err,
                cursor: "pointer",
                fontSize: "10px",
                padding: "2px 4px",
              }}
              title="Remove KPI"
            >{"\u00D7"}</button>
          )}
          <input value={it.label} onChange={e => canEditValues && upd(i, "label", e.target.value)} placeholder="Label" style={{ ...sty, width: "100%", marginBottom: "2px" }} disabled={!canEditValues} />
          <div style={{ display: "flex", gap: "2px" }}>
            <input value={it.value} onChange={e => canEditValues && upd(i, "value", e.target.value)} placeholder="Value" style={{ ...sty, flex: 1 }} disabled={!canEditValues} />
            <input value={it.delta} onChange={e => canEditValues && upd(i, "delta", e.target.value)} placeholder="Delta" style={{ ...sty, flex: 1 }} disabled={!canEditValues} />
            <select value={it.direction} onChange={e => canEditValues && upd(i, "direction", e.target.value as Direction)} style={{ ...sty, width: "50px" }} disabled={!canEditValues}>
              <option value="positive">{"\u2191"}</option><option value="negative">{"\u2193"}</option><option value="neutral">{"\u2013"}</option>
            </select>
          </div>
        </div>
      ))}
      {/* Add button — only in structural-edit mode (Design) */}
      {canEditStructure && items.length < 4 && (
        <button
          type="button"
          onClick={add}
          style={{
            fontSize: "8px",
            fontFamily: TK.font.data,
            background: TK.c.bgAct,
            color: TK.c.acc,
            border: `1px solid ${TK.c.brd}`,
            borderRadius: "2px",
            padding: "3px 8px",
            cursor: "pointer",
            width: "100%",
          }}
        >+ ADD KPI</button>
      )}
    </div>
  );
}
