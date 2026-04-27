'use client';

import React, { memo } from 'react';
import { useTranslations } from 'next-intl';
import type { EditorAction } from '../types';
import { TK } from '../config/tokens';
import { SIZES } from '../config/sizes';
import type { PresetId } from '../config/sizes';

interface ExportPresetsSectionProps {
  currentSize: PresetId;
  exportPresets: readonly PresetId[];
  dispatch: React.Dispatch<EditorAction>;
  canEdit: boolean;
}

/**
 * Phase 2.1 PR#2 — "Export presets" picker.
 *
 * Renders one checkbox per preset in `SIZES` (all 7, including
 * `long_infographic`) — distinct from `EXPORTABLE_PRESET_IDS`, which is
 * the 6-entry legacy single-PNG size picker scope. The Inspector list is
 * the operator opt-in surface for the multi-preset ZIP export per recon
 * Q-2.1-9; both lists coexist with different purposes.
 *
 * The preset matching `page.size` is force-enabled (disabled checkbox,
 * stays checked) AND enforced as a state invariant by
 * `normalizeExportPresets` in the reducer — the current canvas always
 * renders, regardless of what the operator toggles or what arrives from
 * a partial migration. A `current_required` hint surfaces the rule in UI.
 *
 * Toggling a non-current preset dispatches `UPDATE_PAGE_EXPORT_PRESETS`
 * with the next list. The section reads its checked state straight from
 * `exportPresets`; no local component state.
 */
function ExportPresetsSectionImpl({
  currentSize,
  exportPresets,
  dispatch,
  canEdit,
}: ExportPresetsSectionProps) {
  const tExport = useTranslations('inspector.export_presets');
  // Phase 2.1 PR#2 fix1 (P1.3): Inspector enumerates ALL preset IDs from
  // SIZES directly. PR#3 has now expanded EXPORTABLE_PRESET_IDS to also
  // include `long_infographic`, but the two lists remain semantically
  // distinct (size picker = "what canvas am I editing"; this list = "what
  // presets get included in the ZIP"). Reading from SIZES keeps Inspector
  // independent of size-picker scope changes.
  const presetIds = Object.keys(SIZES) as PresetId[];
  const enabled = new Set<string>(exportPresets);

  const togglePreset = (id: PresetId) => {
    if (!canEdit) return;
    if (id === currentSize) return; // current size is force-enabled
    const next: PresetId[] = enabled.has(id)
      ? exportPresets.filter((p) => p !== id)
      : [...exportPresets, id];
    dispatch({ type: 'UPDATE_PAGE_EXPORT_PRESETS', exportPresets: next });
  };

  return (
    <div data-testid="export-presets-section" style={{ marginBottom: '10px' }}>
      <div
        style={{
          fontSize: '8px',
          fontFamily: TK.font.data,
          color: TK.c.txtM,
          textTransform: 'uppercase',
          marginBottom: '3px',
        }}
      >
        {tExport('label')}
      </div>
      <div
        style={{
          fontSize: '8px',
          fontFamily: TK.font.body,
          color: TK.c.txtS,
          marginBottom: '4px',
          lineHeight: 1.5,
        }}
      >
        {tExport('help')}
      </div>
      <div role="group" aria-label={tExport('label')}>
        {presetIds.map((id) => {
          const preset = SIZES[id];
          const isCurrent = id === currentSize;
          const isChecked = isCurrent || enabled.has(id);
          const isDisabled = isCurrent || !canEdit;
          return (
            <label
              key={id}
              data-testid={`export-preset-row-${id}`}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '4px 6px',
                marginBottom: '1px',
                fontSize: '9px',
                background: isChecked ? TK.c.bgAct : 'transparent',
                border: isChecked
                  ? `1px solid ${TK.c.acc}30`
                  : '1px solid transparent',
                borderRadius: '3px',
                cursor: isDisabled ? 'not-allowed' : 'pointer',
                color: TK.c.txtP,
                opacity: !canEdit && !isCurrent ? 0.5 : 1,
              }}
            >
              <input
                type="checkbox"
                data-testid={`export-preset-${id}`}
                checked={isChecked}
                disabled={isDisabled}
                onChange={() => togglePreset(id)}
                aria-label={preset.n}
                style={{ cursor: isDisabled ? 'not-allowed' : 'pointer' }}
              />
              <span>{preset.n}</span>
              <span style={{ color: TK.c.txtM, marginLeft: 'auto' }}>
                {preset.w}
                {'×'}
                {preset.h}
              </span>
            </label>
          );
        })}
      </div>
      <div
        style={{
          fontSize: '7px',
          fontFamily: TK.font.data,
          color: TK.c.txtM,
          marginTop: '4px',
          lineHeight: 1.5,
        }}
      >
        {tExport('current_required')}
      </div>
    </div>
  );
}

export const ExportPresetsSection = memo(ExportPresetsSectionImpl);
