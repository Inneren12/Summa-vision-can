'use client';

import React from 'react';
import { TK } from '../../config/tokens';

interface KPIItem {
  label: string;
  value: string;
  delta: string;
  direction: string;
}

interface KPIItemsEditorProps {
  items: KPIItem[];
  onChange: (items: KPIItem[]) => void;
  editable: boolean;
}

export function KPIItemsEditor({ items, onChange, editable }: KPIItemsEditorProps) {
  const upd = (idx: number, key: keyof KPIItem, val: string) => { const next = [...items]; next[idx] = { ...next[idx], [key]: val }; onChange(next); };
  const sty: React.CSSProperties = { fontSize: "9px", fontFamily: TK.font.data, background: TK.c.bgSurf, color: TK.c.txtP, border: `1px solid ${TK.c.brd}`, borderRadius: "2px", padding: "3px 5px", outline: "none", boxSizing: "border-box" };
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "3px" }}>
      <div style={{ fontSize: "8px", fontFamily: TK.font.data, color: TK.c.txtM, textTransform: "uppercase" }}>KPI CARDS ({items.length})</div>
      {items.map((it, i) => (
        <div key={i} style={{ padding: "4px", border: `1px solid ${TK.c.brd}`, borderRadius: "3px", marginBottom: "3px" }}>
          <input value={it.label} onChange={e => editable && upd(i, "label", e.target.value)} placeholder="Label" style={{ ...sty, width: "100%", marginBottom: "2px" }} disabled={!editable} />
          <div style={{ display: "flex", gap: "2px" }}>
            <input value={it.value} onChange={e => editable && upd(i, "value", e.target.value)} placeholder="Value" style={{ ...sty, flex: 1 }} disabled={!editable} />
            <input value={it.delta} onChange={e => editable && upd(i, "delta", e.target.value)} placeholder="Delta" style={{ ...sty, flex: 1 }} disabled={!editable} />
            <select value={it.direction} onChange={e => editable && upd(i, "direction", e.target.value)} style={{ ...sty, width: "50px" }} disabled={!editable}>
              <option value="positive">{"\u2191"}</option><option value="negative">{"\u2193"}</option><option value="neutral">{"\u2013"}</option>
            </select>
          </div>
        </div>
      ))}
    </div>
  );
}
