'use client';

import React from 'react';
import { TK } from '../../config/tokens';

interface BarItem {
  label: string;
  value: number;
  flag: string;
  highlight: boolean;
  _id?: string;
}

interface BarItemsEditorProps {
  items: BarItem[];
  onChange: (items: BarItem[]) => void;
  editable: boolean;
}

export function BarItemsEditor({ items, onChange, editable }: BarItemsEditorProps) {
  const upd = (idx: number, key: keyof BarItem, val: string | number | boolean) => { const next = [...items]; next[idx] = { ...next[idx], [key]: val }; onChange(next); };
  const del = (idx: number) => onChange(items.filter((_, i) => i !== idx));
  const add = () => onChange([...items, { label: "New", value: 0, flag: "", highlight: false, _id: crypto.randomUUID() }]);
  const sty: React.CSSProperties = { fontSize: "9px", fontFamily: TK.font.data, background: TK.c.bgSurf, color: TK.c.txtP, border: `1px solid ${TK.c.brd}`, borderRadius: "2px", padding: "3px 5px", outline: "none", boxSizing: "border-box" };
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "3px" }}>
      <div style={{ fontSize: "8px", fontFamily: TK.font.data, color: TK.c.txtM, textTransform: "uppercase" }}>DATA ITEMS ({items.length})</div>
      <div style={{ maxHeight: "180px", overflowY: "auto" }}>
        {items.map((it, i) => (
          <div key={it._id || i} style={{ display: "flex", gap: "2px", alignItems: "center", marginBottom: "2px" }}>
            <input value={it.flag || ""} onChange={e => editable && upd(i, "flag", e.target.value)} style={{ ...sty, width: "24px", textAlign: "center" }} disabled={!editable} title="Flag" />
            <input value={it.label} onChange={e => editable && upd(i, "label", e.target.value)} style={{ ...sty, flex: 1 }} disabled={!editable} title="Label" />
            <input type="number" value={it.value} onChange={e => editable && upd(i, "value", parseFloat(e.target.value) || 0)} style={{ ...sty, width: "50px" }} disabled={!editable} title="Value" />
            <button onClick={() => editable && upd(i, "highlight", !it.highlight)} style={{ ...sty, background: it.highlight ? TK.c.acc + "30" : TK.c.bgSurf, color: it.highlight ? TK.c.acc : TK.c.txtM, cursor: editable ? "pointer" : "default", width: "18px", textAlign: "center" }} disabled={!editable} title="Highlight">{"\u2605"}</button>
            {editable && <button onClick={() => del(i)} style={{ ...sty, color: TK.c.err, cursor: "pointer", width: "18px", textAlign: "center" }} title="Remove">{"\u00D7"}</button>}
          </div>
        ))}
      </div>
      {editable && <button onClick={add} style={{ fontSize: "8px", fontFamily: TK.font.data, background: TK.c.bgAct, color: TK.c.acc, border: `1px solid ${TK.c.brd}`, borderRadius: "2px", padding: "3px 8px", cursor: "pointer", width: "100%" }}>+ ADD ITEM</button>}
    </div>
  );
}
