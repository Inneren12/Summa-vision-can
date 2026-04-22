'use client';

import React, { useState } from 'react';
import { useTranslations } from 'next-intl';
import type { SeriesItem, SeriesRole } from '../../types';
import { isSeriesRole } from '../../types';
import { TK } from '../../config/tokens';
import { makeId } from '../../utils/ids';

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
  const tSeries = useTranslations('block.series');
  const tXLabels = useTranslations('block.x_labels');
  const [seriesDrafts, setSeriesDrafts] = useState<Record<string, string>>({});

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

  const updSeriesData = (id: string, rawStr: string) => {
    if (!canEditValues) return;
    setSeriesDrafts(prev => ({ ...prev, [id]: rawStr }));

    // Parse strictly — reject if any value is empty, NaN, or non-finite
    const parts = rawStr.split(",").map(v => v.trim());
    if (parts.some(p => p === "")) return; // don't commit while editing

    const parsed = parts.map(Number);
    if (parsed.some(v => !Number.isFinite(v))) return; // reject NaN/Infinity

    const idx = series.findIndex(s => s._id === id);
    if (idx >= 0) updSeries(idx, "data", parsed);
  };

  const commitSeriesDraft = (id: string) => {
    setSeriesDrafts(prev => {
      const next = { ...prev };
      delete next[id];
      return next;
    });
  };

  const addSeries = () => {
    if (!canEditStructure) return;
    const newData = new Array(xLabels.length).fill(0);
    onChange({
      series: [...series, {
        label: tSeries('new.default_label'),
        role: "secondary" as SeriesRole,
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
      <div style={{ fontSize: "8px", fontFamily: TK.font.data, color: TK.c.txtM, textTransform: "uppercase" }}>{tXLabels('title')}</div>
      {/* xLabels is structural: template mode can edit series values but not axis shape */}
      <input value={xLabels.join(", ")} onChange={e => updXLabels(e.target.value)} style={{ ...sty, width: "100%" }} disabled={!canEditStructure} title={tXLabels('comma_hint.title')} />
      <div style={{ fontSize: "8px", fontFamily: TK.font.data, color: TK.c.txtM, textTransform: "uppercase", marginTop: "4px" }}>{tSeries('title_count', { count: series.length })}</div>
      {series.map((s, i) => (
        <div key={s._id} style={{ padding: "4px", border: `1px solid ${TK.c.brd}`, borderRadius: "3px", position: "relative" }}>
          {/* Remove button — only in structural-edit mode (Design) */}
          {canEditStructure && series.length > 1 && (
            <button
              type="button"
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
              title={tSeries('remove.title')}
            >{"\u00D7"}</button>
          )}
          <div style={{ display: "flex", gap: "2px", marginBottom: "2px" }}>
            <input value={s.label} onChange={e => canEditValues && updSeries(i, "label", e.target.value)} style={{ ...sty, flex: 1 }} disabled={!canEditValues} placeholder={tSeries('name.placeholder')} />
            <select
              value={s.role}
              onChange={e => {
                if (!canEditValues) return;
                const raw = e.target.value;
                // Runtime guard: reject unknown roles instead of trusting the DOM value.
                const role: SeriesRole = isSeriesRole(raw) ? raw : "secondary";
                updSeries(i, "role", role);
              }}
              style={{ ...sty, width: "70px" }}
              disabled={!canEditValues}
            >
              <option value="primary">{tSeries('role.primary')}</option><option value="benchmark">{tSeries('role.benchmark')}</option><option value="secondary">{tSeries('role.secondary')}</option>
            </select>
          </div>
          <input
            value={seriesDrafts[s._id] ?? s.data.join(", ")}
            onChange={e => updSeriesData(s._id, e.target.value)}
            onBlur={() => commitSeriesDraft(s._id)}
            style={{ ...sty, width: "100%" }}
            disabled={!canEditValues}
            title={tSeries('values.comma_hint.title')}
          />
        </div>
      ))}
      {/* Add button — only in structural-edit mode (Design) */}
      {canEditStructure && (
        <button
          type="button"
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
        >{tSeries('add.action')}</button>
      )}
    </div>
  );
}
