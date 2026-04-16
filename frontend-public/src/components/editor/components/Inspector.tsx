'use client';

import React from 'react';
import type { Block, BlockRegistryEntry, EditorAction } from '../types';
import { TK } from '../config/tokens';
import { BarItemsEditor } from './data-editors/BarItemsEditor';
import { KPIItemsEditor } from './data-editors/KPIItemsEditor';
import { LineSeriesEditor } from './data-editors/LineSeriesEditor';

interface InspectorProps {
  selB: Block | null;
  selR: BlockRegistryEntry | null;
  selId: string | null;
  mode: string;
  canEdit: (reg: BlockRegistryEntry, k: string) => boolean;
  dispatch: React.Dispatch<EditorAction>;
}

function badge(st: string) {
  const c: Record<string, string> = { required_locked: TK.c.err, required_editable: TK.c.acc, optional_default: TK.c.pos, optional_available: TK.c.txtM };
  const l: Record<string, string> = { required_locked: "REQ\u00B7\uD83D\uDD12", required_editable: "REQ", optional_default: "OPT\u00B7ON", optional_available: "OPT" };
  return { color: c[st] || TK.c.txtM, label: l[st] || st };
}

export function Inspector({ selB, selR, selId, mode, canEdit, dispatch }: InspectorProps) {
  return (
    <div style={{ width: "250px", minWidth: "250px", borderLeft: `1px solid ${TK.c.brd}`, display: "flex", flexDirection: "column" }}>
      <div style={{ padding: "7px 10px", borderBottom: `1px solid ${TK.c.brd}`, fontSize: "8px", fontFamily: TK.font.data, color: TK.c.txtS, textTransform: "uppercase", letterSpacing: "0.3px", display: "flex", justifyContent: "space-between" }}>
        <span>Inspector {selR ? `\u00B7 ${selR.name}` : ""}</span>
        {mode === "template" && <span style={{ color: TK.c.acc, fontSize: "7px" }}>TPL</span>}
      </div>
      <div style={{ flex: 1, overflowY: "auto", padding: "8px 10px" }}>
        {!selB && <div style={{ fontSize: "10px", color: TK.c.txtM, padding: "20px 0", textAlign: "center", lineHeight: 1.6 }}>Select a block<br />from Blocks tab</div>}
        {selB && selR && selId && (
          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            <div style={{ display: "flex", gap: "6px", alignItems: "center" }}>
              {(() => { const b = badge(selR.status); return <span style={{ fontSize: "8px", fontFamily: TK.font.data, color: b.color, padding: "2px 6px", background: TK.c.bgAct, borderRadius: "2px" }}>{b.label}</span>; })()}
              {!selB.visible && <span style={{ fontSize: "8px", fontFamily: TK.font.data, color: TK.c.txtM }}>HIDDEN</span>}
            </div>

            {/* Standard controls */}
            {selR.ctrl.map(c => {
              const ed = canEdit(selR, c.k);
              return (
                <div key={c.k} style={{ opacity: ed ? 1 : .4 }}>
                  <label style={{ fontSize: "8px", fontFamily: TK.font.data, color: TK.c.txtM, textTransform: "uppercase", letterSpacing: "0.3px", display: "block", marginBottom: "2px" }}>
                    {c.l}{c.ml && <span style={{ float: "right", color: ((selB.props[c.k] || "") + "").replace(/\n/g, "").length > c.ml * .9 ? TK.c.acc : TK.c.txtM }}>{((selB.props[c.k] || "") + "").replace(/\n/g, "").length}/{c.ml}</span>}
                  </label>
                  {c.t === "text" && <input type="text" value={selB.props[c.k] ?? ""} onChange={e => ed && dispatch({ type: "UPDATE_PROP", blockId: selId, key: c.k, value: e.target.value })} maxLength={c.ml} disabled={!ed} style={{ width: "100%", padding: "5px 7px", fontSize: "10px", fontFamily: TK.font.body, background: TK.c.bgSurf, color: TK.c.txtP, border: `1px solid ${TK.c.brd}`, borderRadius: "3px", outline: "none", boxSizing: "border-box" }} />}
                  {c.t === "textarea" && <textarea value={selB.props[c.k] ?? ""} onChange={e => ed && dispatch({ type: "UPDATE_PROP", blockId: selId, key: c.k, value: e.target.value })} maxLength={c.ml} rows={2} disabled={!ed} style={{ width: "100%", padding: "5px 7px", fontSize: "10px", fontFamily: TK.font.body, background: TK.c.bgSurf, color: TK.c.txtP, border: `1px solid ${TK.c.brd}`, borderRadius: "3px", outline: "none", resize: "vertical", boxSizing: "border-box" }} />}
                  {c.t === "seg" && <div style={{ display: "flex", gap: "1px", background: TK.c.bgSurf, borderRadius: "3px", padding: "1px", border: `1px solid ${TK.c.brd}` }}>{c.opts!.map(o => <button key={o} onClick={() => ed && dispatch({ type: "UPDATE_PROP", blockId: selId, key: c.k, value: o })} disabled={!ed} style={{ flex: 1, padding: "3px 2px", fontSize: "8px", fontFamily: TK.font.data, background: selB.props[c.k] === o ? TK.c.bgAct : "transparent", color: selB.props[c.k] === o ? TK.c.acc : TK.c.txtM, border: "none", borderRadius: "2px", cursor: ed ? "pointer" : "not-allowed", textTransform: "uppercase" }}>{o}</button>)}</div>}
                  {c.t === "toggle" && <button onClick={() => ed && dispatch({ type: "UPDATE_PROP", blockId: selId, key: c.k, value: !selB.props[c.k] })} disabled={!ed} style={{ padding: "4px 8px", fontSize: "9px", fontFamily: TK.font.data, background: selB.props[c.k] ? TK.c.acc + "20" : TK.c.bgSurf, color: selB.props[c.k] ? TK.c.acc : TK.c.txtM, border: `1px solid ${selB.props[c.k] ? TK.c.acc + "40" : TK.c.brd}`, borderRadius: "3px", cursor: ed ? "pointer" : "not-allowed", width: "100%", textAlign: "left" }}>{selB.props[c.k] ? "\u2713 On" : "\u25CB Off"}</button>}
                </div>
              );
            })}

            {/* STRUCTURED DATA EDITORS (Stage 2 Polish) */}
            {selB.type === "bar_horizontal" && (
              <BarItemsEditor items={selB.props.items || []} onChange={items => canEdit(selR, "items") && dispatch({ type: "UPDATE_DATA", blockId: selId, data: { items } })} editable={canEdit(selR, "items")} />
            )}
            {selB.type === "comparison_kpi" && (
              <KPIItemsEditor items={selB.props.items || []} onChange={items => canEdit(selR, "items") && dispatch({ type: "UPDATE_DATA", blockId: selId, data: { items } })} editable={canEdit(selR, "items")} />
            )}
            {selB.type === "line_editorial" && (
              <LineSeriesEditor series={selB.props.series || []} xLabels={selB.props.xLabels || []} onChange={data => canEdit(selR, "series") && dispatch({ type: "UPDATE_DATA", blockId: selId, data })} editable={canEdit(selR, "series")} />
            )}

            <div style={{ marginTop: "4px", padding: "5px 7px", background: TK.c.bgSurf, borderRadius: "3px", fontSize: "7px", fontFamily: TK.font.data, color: TK.c.txtM, lineHeight: 1.6 }}>
              <span style={{ color: TK.c.txtS }}>TYPE</span> {selB.type} <span style={{ color: TK.c.txtS }}>STATUS</span> {selR.status}<br />
              <span style={{ color: TK.c.txtS }}>SECTIONS</span> {selR.allowedSections.join(",")} <span style={{ color: TK.c.txtS }}>MAX</span> {selR.maxPerSection || "\u221E"}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
