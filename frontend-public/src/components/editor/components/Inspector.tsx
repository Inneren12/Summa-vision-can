'use client';

import React, { memo } from 'react';
import { useTranslations } from 'next-intl';
import type { Block, BlockRegistryEntry, EditorAction, EditorMode, BarItem, KPIItem, SeriesItem } from '../types';
import type { ContrastIssue } from '../validation/contrast';
import { TK } from '../config/tokens';
import { canEditStructure as permCanEditStructure } from '../store/permissions';
import { BarItemsEditor } from './data-editors/BarItemsEditor';
import { KPIItemsEditor } from './data-editors/KPIItemsEditor';
import { LineSeriesEditor } from './data-editors/LineSeriesEditor';

interface InspectorProps {
  selB: Block | null;
  selR: BlockRegistryEntry | null;
  selId: string | null;
  mode: EditorMode;
  canEdit: (reg: BlockRegistryEntry, k: string) => boolean;
  dispatch: React.Dispatch<EditorAction>;
  contrastIssues: ContrastIssue[];
}

function badgeLabel(tInspector: (key: string) => string, st: string): string {
  switch (st) {
    case 'required_locked':
      return tInspector('badge.required_locked');
    case 'required_editable':
      return tInspector('badge.required_editable');
    case 'optional_default':
      return tInspector('badge.optional_default');
    case 'optional_available':
      return tInspector('badge.optional_available');
    default:
      return 'UNKNOWN';
  }
}

function badge(tInspector: (key: string) => string, st: string) {
  const c: Record<string, string> = { required_locked: TK.c.err, required_editable: TK.c.acc, optional_default: TK.c.pos, optional_available: TK.c.txtM };
  return { color: c[st] || TK.c.txtM, label: badgeLabel(tInspector, st) };
}

// Helper: read an arbitrary prop value with a fallback if it isn't the expected type.
function getStringProp(block: Block, key: string): string {
  const v = block.props[key];
  return typeof v === "string" ? v : "";
}
function getBoolProp(block: Block, key: string): boolean {
  const v = block.props[key];
  return typeof v === "boolean" ? v : false;
}

function InspectorImpl({ selB, selR, selId, mode, canEdit, dispatch, contrastIssues }: InspectorProps) {
  const tInspector = useTranslations('inspector');
  const tBlockType = useTranslations('block.type');
  const tBlockField = useTranslations('block.field');
  const tBlockOption = useTranslations('block.option');
  const tValidation = useTranslations('validation');
  const tCommon = useTranslations('common');
  const statusBadge = selR ? badge(tInspector, selR.status) : null;
  const blockIssues = selId ? contrastIssues.filter(i => i.blockId === selId) : [];

  // Structured-data editor decisions (hoisted out of inline IIFE for clarity).
  // canValues: individual cell/field edits within the block's existing structure
  // are allowed whenever the block itself is not identity-locked.
  // canStruct: add/remove items (and edit xLabels for line chart). Template
  // mode restricts the latter — shape is template-owned.
  const canValues = selR ? selR.status !== "required_locked" : false;
  const canStruct = selR ? permCanEditStructure(selR, mode) : false;

  let dataEditor: React.ReactNode = null;
  if (selB && selR && selId) {
    if (selB.type === "bar_horizontal") {
      const items = selB.props.items as BarItem[];
      dataEditor = (
        <BarItemsEditor
          items={items}
          onChange={items => dispatch({ type: "UPDATE_DATA", blockId: selId, data: { items } })}
          canEditValues={canValues}
          canEditStructure={canStruct}
        />
      );
    } else if (selB.type === "comparison_kpi") {
      const items = selB.props.items as KPIItem[];
      dataEditor = (
        <KPIItemsEditor
          items={items}
          onChange={items => dispatch({ type: "UPDATE_DATA", blockId: selId, data: { items } })}
          canEditValues={canValues}
          canEditStructure={canStruct}
        />
      );
    } else if (selB.type === "line_editorial") {
      const series = selB.props.series as SeriesItem[];
      const xLabels = selB.props.xLabels as string[];
      dataEditor = (
        <LineSeriesEditor
          series={series}
          xLabels={xLabels}
          onChange={data => dispatch({ type: "UPDATE_DATA", blockId: selId, data })}
          canEditValues={canValues}
          canEditStructure={canStruct}
        />
      );
    }
  }

  return (
    <div style={{ width: "100%", display: "flex", flexDirection: "column" }}>
      <div style={{ padding: "7px 10px", borderBottom: `1px solid ${TK.c.brd}`, fontSize: "8px", fontFamily: TK.font.data, color: TK.c.txtS, textTransform: "uppercase", letterSpacing: "0.3px", display: "flex", justifyContent: "space-between" }}>
        <span>{tInspector('title')} {selR ? `\u00B7 ${selB ? tBlockType(`${selB.type}.name`) : selR.name}` : ""}</span>
        {mode === "template" && <span style={{ color: TK.c.acc, fontSize: "7px" }}>{tInspector('template_mode.short')}</span>}
      </div>
      <div style={{ flex: 1, overflowY: "auto", padding: "8px 10px" }}>
        {!selB && <div style={{ fontSize: "10px", color: TK.c.txtM, padding: "20px 0", textAlign: "center", lineHeight: 1.6 }}>{tInspector('empty.select_block')}<br />{tInspector('empty.from_blocks_tab')}</div>}
        {selB && selR && selId && (
          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            {statusBadge && (
              <div style={{ display: "flex", gap: "6px", alignItems: "center" }}>
                <span style={{ fontSize: "8px", fontFamily: TK.font.data, color: statusBadge.color, padding: "2px 6px", background: TK.c.bgAct, borderRadius: "2px" }}>{statusBadge.label}</span>
                {!selB.visible && <span style={{ fontSize: "8px", fontFamily: TK.font.data, color: TK.c.txtM }}>{tInspector('hidden.status')}</span>}
              </div>
            )}

            {blockIssues.length > 0 && (
              <div data-testid="inspector-contrast" style={{ padding: "6px 8px", borderRadius: "3px", background: TK.c.bgSurf, border: `1px solid ${TK.c.brd}` }}>
                <div style={{ fontSize: "8px", fontFamily: TK.font.data, color: TK.c.txtM, textTransform: "uppercase", letterSpacing: "0.3px", marginBottom: "4px" }}>{tValidation('contrast.title')}</div>
                {blockIssues.map((issue, idx) => (
                  <div key={idx} style={{ fontSize: "10px", fontFamily: TK.font.body, color: issue.severity === "error" ? TK.c.err : TK.c.acc, display: "flex", alignItems: "center", gap: "4px", marginTop: idx === 0 ? 0 : "2px" }}>
                    <span aria-hidden="true">{issue.severity === "error" ? "\u2717" : "!"}</span>
                    <span>
                      {issue.ratio.toFixed(2)}:1 vs {issue.threshold.toFixed(1)}:1
                      {issue.bgPoint === "lightestStop" ? tValidation('contrast.gradient_suffix') : ""}
                    </span>
                  </div>
                ))}
              </div>
            )}

            {/* Standard controls */}
            {selR.ctrl.map(c => {
              const ed = canEdit(selR, c.k);
              const strVal = getStringProp(selB, c.k);
              const boolVal = getBoolProp(selB, c.k);
              const charLen = strVal.replace(/\n/g, "").length;
              return (
                <div key={c.k} style={{ opacity: ed ? 1 : .4 }}>
                  <label style={{ fontSize: "8px", fontFamily: TK.font.data, color: TK.c.txtM, textTransform: "uppercase", letterSpacing: "0.3px", display: "block", marginBottom: "2px" }}>
                    {tBlockField.has(`${c.k}.label`)
                      ? tBlockField(`${c.k}.label`)
                      : tBlockField.has(`${c.k}.short_label`)
                        ? tBlockField(`${c.k}.short_label`)
                        : c.l}
                    {c.ml && <span style={{ float: "right", color: charLen > c.ml * .9 ? TK.c.acc : TK.c.txtM }}>{charLen}/{c.ml}</span>}
                  </label>
                  {c.t === "text" && <input type="text" value={strVal} onChange={e => ed && dispatch({ type: "UPDATE_PROP", blockId: selId, key: c.k, value: e.target.value })} maxLength={c.ml} disabled={!ed} style={{ width: "100%", padding: "5px 7px", fontSize: "10px", fontFamily: TK.font.body, background: TK.c.bgSurf, color: TK.c.txtP, border: `1px solid ${TK.c.brd}`, borderRadius: "3px", outline: "none", boxSizing: "border-box" }} />}
                  {c.t === "textarea" && <textarea value={strVal} onChange={e => ed && dispatch({ type: "UPDATE_PROP", blockId: selId, key: c.k, value: e.target.value })} maxLength={c.ml} rows={2} disabled={!ed} style={{ width: "100%", padding: "5px 7px", fontSize: "10px", fontFamily: TK.font.body, background: TK.c.bgSurf, color: TK.c.txtP, border: `1px solid ${TK.c.brd}`, borderRadius: "3px", outline: "none", resize: "vertical", boxSizing: "border-box" }} />}
                  {c.t === "seg" && <div style={{ display: "flex", gap: "1px", background: TK.c.bgSurf, borderRadius: "3px", padding: "1px", border: `1px solid ${TK.c.brd}` }}>{c.opts!.map(o => <button type="button" key={o} onClick={() => ed && dispatch({ type: "UPDATE_PROP", blockId: selId, key: c.k, value: o })} disabled={!ed} style={{ flex: 1, padding: "3px 2px", fontSize: "8px", fontFamily: TK.font.data, background: strVal === o ? TK.c.bgAct : "transparent", color: strVal === o ? TK.c.acc : TK.c.txtM, border: "none", borderRadius: "2px", cursor: ed ? "pointer" : "not-allowed", textTransform: "uppercase" }}>{tBlockOption.has(`${c.k}.${o}`) ? tBlockOption(`${c.k}.${o}`) : o}</button>)}</div>}
                  {c.t === "toggle" && <button type="button" onClick={() => ed && dispatch({ type: "UPDATE_PROP", blockId: selId, key: c.k, value: !boolVal })} disabled={!ed} style={{ padding: "4px 8px", fontSize: "9px", fontFamily: TK.font.data, background: boolVal ? TK.c.acc + "20" : TK.c.bgSurf, color: boolVal ? TK.c.acc : TK.c.txtM, border: `1px solid ${boolVal ? TK.c.acc + "40" : TK.c.brd}`, borderRadius: "3px", cursor: ed ? "pointer" : "not-allowed", width: "100%", textAlign: "left" }}>{boolVal ? tCommon('toggle.on') : tCommon('toggle.off')}</button>}
                </div>
              );
            })}

            {/* STRUCTURED DATA EDITORS (Stage 2 Polish)
                Permission model: canEditValues lets users edit values within
                existing structure; canEditStructure lets users add/remove items
                (and edit xLabels for line chart). Template mode restricts the
                latter — shape is template-owned. */}
            {dataEditor}

            <div style={{ marginTop: "4px", padding: "5px 7px", background: TK.c.bgSurf, borderRadius: "3px", fontSize: "7px", fontFamily: TK.font.data, color: TK.c.txtM, lineHeight: 1.6 }}>
              <span style={{ color: TK.c.txtS }}>{tInspector('meta.type')}</span> {selB.type} <span style={{ color: TK.c.txtS }}>{tInspector('meta.status')}</span> {selR.status}<br />
              <span style={{ color: TK.c.txtS }}>{tInspector('meta.sections')}</span> {selR.allowedSections.join(",")} <span style={{ color: TK.c.txtS }}>{tInspector('meta.max')}</span> {selR.maxPerSection || "\u221E"}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export const Inspector = memo(InspectorImpl);
