import enMessages from '../../messages/en.json';
import ruMessages from '../../messages/ru.json';
import { BREG } from '../../src/components/editor/registry/blocks';

function get(obj: any, path: string[]): any {
  return path.reduce((acc, key) => acc?.[key], obj);
}

describe('i18n catalog coverage', () => {
  it('every BREG ctrl.k has a matching block.field.{k}.{labelKind} in both locales', () => {
    const missing: string[] = [];
    for (const [blockType, entry] of Object.entries(BREG)) {
      for (const ctrl of entry.ctrl ?? []) {
        const kind = ctrl.labelKind ?? 'label';
        const path = ['block', 'field', ctrl.k, kind];
        if (!get(enMessages, path)) missing.push(`en: ${path.join('.')} (from ${blockType})`);
        if (!get(ruMessages, path)) missing.push(`ru: ${path.join('.')} (from ${blockType})`);
      }
    }
    expect(missing).toEqual([]);
  });

  it('every BREG ctrl.opts value has a matching block.option.{k}.{opt} in both locales', () => {
    const missing: string[] = [];
    for (const [blockType, entry] of Object.entries(BREG)) {
      for (const ctrl of entry.ctrl ?? []) {
        if (!ctrl.opts) continue;
        for (const opt of ctrl.opts) {
          const path = ['block', 'option', ctrl.k, opt];
          if (!get(enMessages, path)) missing.push(`en: ${path.join('.')} (from ${blockType})`);
          if (!get(ruMessages, path)) missing.push(`ru: ${path.join('.')} (from ${blockType})`);
        }
      }
    }
    expect(missing).toEqual([]);
  });

  it('every BREG block type has a matching block.type.{type}.name in both locales', () => {
    const missing: string[] = [];
    for (const blockType of Object.keys(BREG)) {
      const path = ['block', 'type', blockType, 'name'];
      if (!get(enMessages, path)) missing.push(`en: ${path.join('.')}`);
      if (!get(ruMessages, path)) missing.push(`ru: ${path.join('.')}`);
    }
    expect(missing).toEqual([]);
  });
});
