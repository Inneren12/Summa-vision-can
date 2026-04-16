'use client';

import React, { useState } from 'react';
import { TK } from '../../config/tokens';
import { makeId } from '../../utils/ids';

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
  // canEditValues: user can edit series label/role/data-values within existing structure
  canEditValues: boolean;
  // canEditStructure: user can add/remove series AND edit xLabels
  //   (xLabels is structural because changing it alters the shape of every series)
  canEditStructure: boolean;
}

export function LineSeriesEditor({ series, xLabels, onChange, canEditValues, canEditStructure }: LineSeriesEditorProps) {
  const [seriesDrafts, setSeriesDrafts] = useState<Record<number, string>>({});

  const updSeries = <K extends keyof SeriesItem>(idx: number, key: K, val: SeriesItem[K]) => {
    const next = [...series];
    next[idx] = { ...next[idx], [key]: val };
    onChange({ series: next, xLabels });
  };

  const updXLabels = (rawStr: string) => {
    if (!canEditStructure) return;
    const newLabels = rawStr.split(",").map(s => s.trim()).filter(Boolean);
    if (newLabels.length === 0) return;

    // Auto-sync: truncate or pad each series.data to match newLabels.length
    const syncedSeries = series.map(s => {
      const data = [...s.data];
      if (data.length < newLabels.length) {
        while (data.length < newLabels.length) data.push(0);
      } else if (data.length > newLabels.length) {
        data.length = newLabels.length;
      }
      return { ...s, data };
    });

    onChange({ series: syncedSeries, xLabels: newLabels });
  };

  const updSeriesData = (idx: number, rawStr: string) => {
    if (!canEditValues) return;
    setSeriesDrafts(prev => ({ ...prev, [idx]: rawStr }));

    // Parse strictly — reject if any value is empty, NaN, or non-finite
    const parts = rawStr.split(",").map(v => v.trim());
    if (parts.some(p => p === "")) return; // don't commit while editing

    const parsed = parts.map(Number);
    if (parsed.some(v => !Number.isFinite(v))) return; // reject NaN/Infinity

    updSeries(idx, "data", parsed);
  };

  const commitSeriesDraft = (idx: number) => {
    setSeriesDrafts(prev => {
      const next = { ...prev };
      delete next[idx];
      return next;
    });
  };

  const addSeries = () => {
    if (!canEditStructure) return;
    const newData = new Array(xLabels.length).fill(0);
    onChange({
      series: [...series, {
        label: "New Series",
        role: "secondary",
        data: newData,
        _id: makeId(),
      }],
      xLabels,
    });
  };

  const removeSeries = (idx: number) => {
    if (!canEditStructure) return;
    if (series.length <= 1) return; // need at least 1 series
    onChange({
      series: series.filter((_, i) => i !== idx),
      xLabels,
    });
  };

  const sty: React.CSSProperties = { fontSize: "9px", fontFamily: TK.font.data, background: TK.c.bgSurf, color: TK.c.txtP, border: `1px solid ${TK.c.brd}`, borderRadius: "2px", padding: "3px 5px", outline: "none", boxSizing: "border-box" };
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
      <div style={{ fontSize: "8px", fontFamily: TK.font.data, color: TK.c.txtM, textTransform: "uppercase" }}>X LABELS</div>
      {/* xLabels is structural: template mode can edit series values but not axis shape */}
      <input value={xLabels.join(", ")} onChange={e => updXLabels(e.target.value)} style={{ ...sty, width: "100%" }} disabled={!canEditStructure} title="Comma-separated labels" />
      <div style={{ fontSize: "8px", fontFamily: TK.font.data, color: TK.c.txtM, textTransform: "uppercase", marginTop: "4px" }}>SERIES ({series.length})</div>
      {series.map((s, i) => (
        <div key={s._id || i} style={{ padding: "4px", border: `1px solid ${TK.c.brd}`, borderRadius: "3px", position: "relative" }}>
          {/* Remove button — only in structural-edit mode (Design) */}
          {canEditStructure && series.length > 1 && (
            <button
              onClick={() => removeSeries(i)}
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
              title="Remove series"
            >{"\u00D7"}</button>
          )}
          <div style={{ display: "flex", gap: "2px", marginBottom: "2px" }}>
            <input value={s.label} onChange={e => canEditValues && updSeries(i, "label", e.target.value)} style={{ ...sty, flex: 1 }} disabled={!canEditValues} placeholder="Series name" />
            <select value={s.role} onChange={e => canEditValues && updSeries(i, "role", e.target.value)} style={{ ...sty, width: "70px" }} disabled={!canEditValues}>
              <option value="primary">Primary</option><option value="benchmark">Benchmark</option><option value="secondary">Secondary</option>
            </select>
          </div>
          <input
            value={seriesDrafts[i] ?? s.data.join(", ")}
            onChange={e => updSeriesData(i, e.target.value)}
            onBlur={() => commitSeriesDraft(i)}
            style={{ ...sty, width: "100%" }}
            disabled={!canEditValues}
            title="Comma-separated values"
          />
        </div>
      ))}
      {/* Add button — only in structural-edit mode (Design) */}
      {canEditStructure && (
        <button
          onClick={addSeries}
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
        >+ ADD SERIES</button>
      )}
    </div>
  );
}
