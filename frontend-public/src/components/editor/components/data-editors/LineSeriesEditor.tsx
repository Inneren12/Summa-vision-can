'use client';

import React, { useState } from 'react';
import { TK } from '../../config/tokens';

interface SeriesItem {
  label: string;
  data: number[];
  role: string;
  _id?: string;
}

interface LineSeriesEditorProps {
  series: SeriesItem[];
  xLabels: string[];
  onChange: (data: { series: SeriesItem[]; xLabels: string[] }) => void;
  editable: boolean;
}

export function LineSeriesEditor({ series, xLabels, onChange, editable }: LineSeriesEditorProps) {
  const [seriesDrafts, setSeriesDrafts] = useState<Record<number, string>>({});

  const updSeries = <K extends keyof SeriesItem>(idx: number, key: K, val: SeriesItem[K]) => {
    const next = [...series];
    next[idx] = { ...next[idx], [key]: val };
    onChange({ series: next, xLabels });
  };
  const updXL = (val: string) => onChange({ series, xLabels: val.split(",").map(s => s.trim()) });

  const updSeriesData = (idx: number, rawStr: string) => {
    setSeriesDrafts(prev => ({ ...prev, [idx]: rawStr }));
    // Commit only if all values parse cleanly
    const parsed = rawStr.split(",").map(v => Number(v.trim()));
    if (parsed.length > 0 && parsed.every(v => !Number.isNaN(v))) {
      updSeries(idx, "data", parsed);
    }
  };

  const sty: React.CSSProperties = { fontSize: "9px", fontFamily: TK.font.data, background: TK.c.bgSurf, color: TK.c.txtP, border: `1px solid ${TK.c.brd}`, borderRadius: "2px", padding: "3px 5px", outline: "none", boxSizing: "border-box" };
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
      <div style={{ fontSize: "8px", fontFamily: TK.font.data, color: TK.c.txtM, textTransform: "uppercase" }}>X LABELS</div>
      <input value={xLabels.join(", ")} onChange={e => editable && updXL(e.target.value)} style={{ ...sty, width: "100%" }} disabled={!editable} title="Comma-separated labels" />
      <div style={{ fontSize: "8px", fontFamily: TK.font.data, color: TK.c.txtM, textTransform: "uppercase", marginTop: "4px" }}>SERIES ({series.length})</div>
      {series.map((s, i) => (
        <div key={s._id || i} style={{ padding: "4px", border: `1px solid ${TK.c.brd}`, borderRadius: "3px" }}>
          <div style={{ display: "flex", gap: "2px", marginBottom: "2px" }}>
            <input value={s.label} onChange={e => editable && updSeries(i, "label", e.target.value)} style={{ ...sty, flex: 1 }} disabled={!editable} placeholder="Series name" />
            <select value={s.role} onChange={e => editable && updSeries(i, "role", e.target.value)} style={{ ...sty, width: "70px" }} disabled={!editable}>
              <option value="primary">Primary</option><option value="benchmark">Benchmark</option><option value="secondary">Secondary</option>
            </select>
          </div>
          <input
            value={seriesDrafts[i] ?? s.data.join(", ")}
            onChange={e => editable && updSeriesData(i, e.target.value)}
            onBlur={() => setSeriesDrafts(prev => { const next = { ...prev }; delete next[i]; return next; })}
            style={{ ...sty, width: "100%" }}
            disabled={!editable}
            title="Comma-separated values"
          />
        </div>
      ))}
    </div>
  );
}
