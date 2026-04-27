'use client';

import React, { memo, useMemo } from 'react';
import { useTranslations } from 'next-intl';
import type { CanonicalDocument, EditorAction, PermissionSet, BlockRegistryEntry, LeftTab, TemplateEntry } from '../types';
import { TK } from '../config/tokens';
import { PALETTES } from '../config/palettes';
import { BGS } from '../config/backgrounds';
import { SIZES, EXPORTABLE_PRESET_IDS } from '../config/sizes';
import { BREG } from '../registry/blocks';
import { TPLS } from '../registry/templates';
import { badgeColor, badgeLabel } from '../utils/badge';
import {
  buildThreads,
  isThreadResolved,
  threadUnresolvedCount,
} from '../store/comments';

// TPLS is a module-level constant, so the family grouping is too. If Stage 3+
// makes templates runtime-loaded, this should move back into a useMemo keyed
// on whatever source drives it.
const TEMPLATE_FAMILIES: Record<string, Array<{ id: string } & TemplateEntry>> = (() => {
  const result: Record<string, Array<{ id: string } & TemplateEntry>> = {};
  Object.entries(TPLS).forEach(([id, t]) => {
    if (!result[t.fam]) result[t.fam] = [];
    result[t.fam].push({ id, ...t });
  });
  return result;
})();

interface LeftPanelProps {
  doc: CanonicalDocument;
  dispatch: React.Dispatch<EditorAction>;
  selId: string | null;
  ltab: LeftTab;
  setLtab: (t: LeftTab) => void;
  // Combined mode × workflow permission set computed at the parent
  // (index.tsx). LeftPanel drives button disable state off this alone —
  // raw PERMS[mode] is insufficient because it ignores workflow lockdown.
  effectivePerms: PermissionSet;
}

const tb = (a: boolean): React.CSSProperties => ({ padding: "5px 7px", fontSize: "8px", fontFamily: TK.font.data, textTransform: "uppercase", letterSpacing: "0.4px", cursor: "pointer", background: a ? TK.c.bgAct : "transparent", color: a ? TK.c.acc : TK.c.txtM, border: "none", borderBottom: a ? `2px solid ${TK.c.acc}` : "2px solid transparent", whiteSpace: "nowrap" });

function LeftPanelImpl({ doc, dispatch, selId, ltab, setLtab, effectivePerms }: LeftPanelProps) {
  const tLeftPanel = useTranslations('left_panel');
  const tBlock = useTranslations('block');
  const tBlockType = useTranslations('block.type');
  const tInspector = useTranslations('inspector');
  const tTheme = useTranslations('theme');
  const tReview = useTranslations('review');
  const tTemplateVariant = useTranslations('template.variant');
  const tTemplateDesc = useTranslations('template.desc');
  const canToggle = (reg: BlockRegistryEntry) => effectivePerms.toggleVisibility(reg);

  const unresolvedByBlock = useMemo(() => {
    const threads = buildThreads(doc.review.comments);
    const m = new Map<string, number>();
    for (const t of threads) {
      if (isThreadResolved(t)) continue;
      m.set(t.blockId, (m.get(t.blockId) ?? 0) + threadUnresolvedCount(t));
    }
    return m;
  }, [doc.review.comments]);
  const tabIds = {
    templates: "left-tab-templates",
    blocks: "left-tab-blocks",
    theme: "left-tab-theme",
  } as const;
  const panelIds = {
    templates: "left-panel-templates",
    blocks: "left-panel-blocks",
    theme: "left-panel-theme",
  } as const;

  return (
    <div style={{ width: "220px", minWidth: "220px", borderRight: `1px solid ${TK.c.brd}`, display: "flex", flexDirection: "column" }}>
      <div role="tablist" aria-label={tLeftPanel('sections.aria')} style={{ display: "flex", borderBottom: `1px solid ${TK.c.brd}` }}>
        {([
          ["templates", tLeftPanel('tab.templates.short')],
          ["blocks", tLeftPanel('tab.blocks.short')],
          ["theme", tLeftPanel('tab.theme.short')],
        ] as const).map(([k, l]) => <button type="button" key={k} id={tabIds[k]} role="tab" aria-selected={ltab === k} aria-controls={panelIds[k]} aria-label={tLeftPanel('tab.aria', { name: l })} onClick={() => setLtab(k)} style={tb(ltab === k)}>{l}</button>)}
      </div>
      <div
        id={panelIds[ltab]}
        role="tabpanel"
        aria-labelledby={tabIds[ltab]}
        style={{ flex: 1, overflowY: "auto", padding: "8px" }}
      >
        {ltab === "templates" && Object.entries(TEMPLATE_FAMILIES).map(([f, ts]) => (
          <div key={f} style={{ marginBottom: "10px" }}>
            <div style={{ fontSize: "8px", fontFamily: TK.font.data, color: TK.c.txtM, textTransform: "uppercase", letterSpacing: "0.4px", marginBottom: "3px" }}>{f}</div>
            <div role="radiogroup" aria-label={`${f} templates`}>
              {ts.map(t => <button type="button" role="radio" key={t.id} onClick={() => effectivePerms.switchTemplate && dispatch({ type: "SWITCH_TPL", tid: t.id })} disabled={!effectivePerms.switchTemplate} aria-label={`Template ${tTemplateVariant(t.variantKey)} — ${tTemplateDesc(t.descKey)}`} aria-checked={doc.templateId === t.id} style={{ display: "block", width: "100%", textAlign: "left", padding: "6px 8px", marginBottom: "2px", background: doc.templateId === t.id ? TK.c.bgAct : TK.c.bgSurf, border: `1px solid ${doc.templateId === t.id ? TK.c.acc + "40" : TK.c.brd}`, borderRadius: "4px", cursor: effectivePerms.switchTemplate ? "pointer" : "not-allowed", color: TK.c.txtP, opacity: (!effectivePerms.switchTemplate && doc.templateId !== t.id) ? 0.4 : 1 }}>
                <div style={{ fontSize: "10px", fontWeight: 500 }}>{tTemplateVariant(t.variantKey)}</div>
                <div style={{ fontSize: "8px", color: TK.c.txtM, marginTop: "1px" }}>{tTemplateDesc(t.descKey)}</div>
              </button>)}
            </div>
          </div>
        ))}
        {ltab === "blocks" && doc.sections.map(sec => (
          <div key={sec.id} style={{ marginBottom: "6px" }}>
            <div style={{ fontSize: "7px", fontFamily: TK.font.data, color: TK.c.txtM, textTransform: "uppercase", padding: "2px 0" }}>{sec.type}</div>
            {sec.blockIds.map(bid => {
              const b = doc.blocks[bid];
              if (!b) return null;
              const r = BREG[b.type];
              if (!r) return null;
              const unresolved = unresolvedByBlock.get(bid) ?? 0;
              return (
                <div key={bid} style={{ display: "flex", alignItems: "center", gap: "3px", marginBottom: "1px" }}>
                  <button type="button" onClick={() => dispatch({ type: "SELECT", blockId: bid })} aria-label={tBlock('select.aria', { name: tBlockType(`${b.type}.name`) })} aria-pressed={selId === bid} style={{ flex: 1, display: "flex", alignItems: "center", gap: "4px", textAlign: "left", padding: "4px 6px", fontSize: "9px", background: selId === bid ? TK.c.bgAct : "transparent", border: selId === bid ? `1px solid ${TK.c.acc}30` : "1px solid transparent", borderRadius: "3px", cursor: "pointer", color: b.visible ? TK.c.txtP : TK.c.txtM, textDecoration: b.visible ? "none" : "line-through", opacity: b.visible ? 1 : .5 }}>
                    <span style={{ fontSize: "6px", color: badgeColor(r.status, TK.c) }}>{badgeLabel(tInspector, r.status)}</span><span>{tBlockType(`${b.type}.name`)}</span>
                    {unresolved > 0 && (
                      <span
                        data-testid="block-unresolved-pill"
                        data-block-id={bid}
                        title={tReview('unresolved_comments.title_count', { count: unresolved })}
                        style={{ marginLeft: "auto", padding: "1px 5px", background: TK.c.accM, color: TK.c.acc, borderRadius: "2px", fontFamily: TK.font.data, fontSize: "8px" }}
                      >{unresolved}</span>
                    )}
                  </button>
                  {canToggle(r) && <button type="button" onClick={() => dispatch({ type: "TOGGLE_VIS", blockId: bid })} aria-label={b.visible ? tBlock('visibility.hide.aria', { name: tBlockType(`${b.type}.name`) }) : tBlock('visibility.show.aria', { name: tBlockType(`${b.type}.name`) })} aria-pressed={b.visible} title={b.visible ? tBlock('visibility.hide.title') : tBlock('visibility.show.title')} style={{ background: "none", border: "none", color: b.visible ? TK.c.pos : TK.c.txtM, cursor: "pointer", fontSize: "10px", padding: "2px 4px" }}>{b.visible ? "\u25C9" : "\u25CB"}</button>}
                </div>
              );
            })}
          </div>
        ))}
        {ltab === "theme" && (
          <>
            <div style={{ marginBottom: "10px" }}>
              <div style={{ fontSize: "8px", fontFamily: TK.font.data, color: TK.c.txtM, textTransform: "uppercase", marginBottom: "3px" }}>{tTheme('palette.title')}</div>
              {Object.entries(PALETTES).map(([k, v]) => <button type="button" key={k} onClick={() => effectivePerms.changePalette && dispatch({ type: "CHANGE_PAGE", key: "palette", value: k })} disabled={!effectivePerms.changePalette} aria-label={tTheme('option.palette.aria', { name: v.n })} aria-pressed={doc.page.palette === k} style={{ display: "flex", alignItems: "center", gap: "6px", width: "100%", textAlign: "left", padding: "4px 6px", marginBottom: "1px", fontSize: "9px", background: doc.page.palette === k ? TK.c.bgAct : "transparent", border: doc.page.palette === k ? `1px solid ${TK.c.acc}30` : "1px solid transparent", borderRadius: "3px", cursor: effectivePerms.changePalette ? "pointer" : "not-allowed", color: TK.c.txtP, opacity: effectivePerms.changePalette ? 1 : 0.5 }}><div style={{ width: "10px", height: "10px", borderRadius: "2px", background: v.p }} />{v.n}</button>)}
            </div>
            <div style={{ marginBottom: "10px" }}>
              <div style={{ fontSize: "8px", fontFamily: TK.font.data, color: TK.c.txtM, textTransform: "uppercase", marginBottom: "3px" }}>{tTheme('background.title')}</div>
              {Object.entries(BGS).map(([k, v]) => <button type="button" key={k} onClick={() => effectivePerms.changeBackground && dispatch({ type: "CHANGE_PAGE", key: "background", value: k })} disabled={!effectivePerms.changeBackground} aria-label={tTheme('option.background.aria', { name: v.n })} aria-pressed={doc.page.background === k} style={{ display: "block", width: "100%", textAlign: "left", padding: "4px 6px", marginBottom: "1px", fontSize: "9px", background: doc.page.background === k ? TK.c.bgAct : "transparent", border: doc.page.background === k ? `1px solid ${TK.c.acc}30` : "1px solid transparent", borderRadius: "3px", cursor: effectivePerms.changeBackground ? "pointer" : "not-allowed", color: TK.c.txtP, opacity: effectivePerms.changeBackground ? 1 : 0.5 }}>{v.n}</button>)}
            </div>
            <div>
              <div style={{ fontSize: "8px", fontFamily: TK.font.data, color: TK.c.txtM, textTransform: "uppercase", marginBottom: "3px" }}>{tTheme('size.title')}</div>
              {EXPORTABLE_PRESET_IDS.map((k) => { const v = SIZES[k]; return <button type="button" key={k} onClick={() => effectivePerms.changeSize && dispatch({ type: "CHANGE_PAGE", key: "size", value: k })} disabled={!effectivePerms.changeSize} aria-label={tTheme('option.size.aria', { name: v.n, width: v.w, height: v.h })} aria-pressed={doc.page.size === k} style={{ display: "block", width: "100%", textAlign: "left", padding: "4px 6px", marginBottom: "1px", fontSize: "9px", background: doc.page.size === k ? TK.c.bgAct : "transparent", border: doc.page.size === k ? `1px solid ${TK.c.acc}30` : "1px solid transparent", borderRadius: "3px", cursor: effectivePerms.changeSize ? "pointer" : "not-allowed", color: TK.c.txtP, opacity: effectivePerms.changeSize ? 1 : 0.5 }}>{v.n} <span style={{ color: TK.c.txtM }}>{v.w}{"\u00D7"}{v.h}</span></button>; })}
            </div>
          </>
        )}
      </div>
      <div style={{ padding: "4px 8px", borderTop: `1px solid ${TK.c.brd}`, fontSize: "7px", fontFamily: TK.font.data, color: TK.c.txtM }}>
        {tLeftPanel('footer.summary', {
          schema: doc.schemaVersion,
          sections: doc.sections.length,
          blocks: Object.keys(doc.blocks).length,
        })}
      </div>
    </div>
  );
}

export const LeftPanel = memo(LeftPanelImpl);
