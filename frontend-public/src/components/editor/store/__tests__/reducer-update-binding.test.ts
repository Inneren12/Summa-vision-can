import { reducer, initState } from '../reducer';
import { BREG } from '../../registry/blocks';
import type { EditorState } from '../../types';
import type { SingleValueBinding } from '../../binding/types';

function baseState(): EditorState {
  const s = initState();
  const reg = BREG.hero_stat;
  if (!reg) throw new Error('hero_stat missing from registry');
  const blockId = 'blk_hero';
  return {
    ...s,
    doc: {
      ...s.doc,
      sections: [{ id: 'sec_hero', type: 'hero', blockIds: [blockId] }],
      blocks: {
        [blockId]: {
          id: blockId,
          type: 'hero_stat',
          props: { ...reg.dp },
          visible: true,
        },
      },
    },
  };
}

const BLOCK_ID = 'blk_hero';
const validBinding: SingleValueBinding = {
  kind: 'single',
  cube_id: '18100004',
  semantic_key: 'rate_5yr_fixed',
  filters: { geo: 'CA' },
  period: '2024-Q3',
};

describe('reducer / UPDATE_BINDING (Phase 3.1d Slice 3a)', () => {
  it('sets binding when payload.binding is present', () => {
    const s0 = baseState();
    const s1 = reducer(s0, { type: 'UPDATE_BINDING', blockId: BLOCK_ID, binding: validBinding });
    expect(s1.doc.blocks[BLOCK_ID].binding).toEqual(validBinding);
    expect(s1.dirty).toBe(true);
  });

  it('removes binding when payload.binding is undefined', () => {
    const s0 = baseState();
    const s1 = reducer(s0, { type: 'UPDATE_BINDING', blockId: BLOCK_ID, binding: validBinding });
    const s2 = reducer(s1, { type: 'UPDATE_BINDING', blockId: BLOCK_ID, binding: undefined });
    expect(s2.doc.blocks[BLOCK_ID]).not.toHaveProperty('binding');
  });

  it('rejects with reason when blockId does not exist (no doc mutation)', () => {
    const s0 = baseState();
    const s1 = reducer(s0, {
      type: 'UPDATE_BINDING',
      blockId: 'blk_nonexistent',
      binding: validBinding,
    });
    expect(s1.doc).toBe(s0.doc);
    expect(s1._lastRejection?.type).toBe('UPDATE_BINDING');
    expect(s1._lastRejection?.reason).toMatch(/not found/);
  });

  it('rejects with reason when block is locked', () => {
    const s0 = baseState();
    const s1: EditorState = {
      ...s0,
      doc: {
        ...s0.doc,
        blocks: {
          ...s0.doc.blocks,
          [BLOCK_ID]: { ...s0.doc.blocks[BLOCK_ID], locked: true },
        },
      },
    };
    const s2 = reducer(s1, { type: 'UPDATE_BINDING', blockId: BLOCK_ID, binding: validBinding });
    expect(s2.doc.blocks[BLOCK_ID]).not.toHaveProperty('binding');
    expect(s2._lastRejection?.type).toBe('UPDATE_BINDING');
    expect(s2._lastRejection?.reason).toMatch(/locked/);
  });

  it('rejects in template mode (binding edits are design-mode)', () => {
    const s0 = baseState();
    const s1: EditorState = { ...s0, mode: 'template' };
    const s2 = reducer(s1, { type: 'UPDATE_BINDING', blockId: BLOCK_ID, binding: validBinding });
    expect(s2.doc.blocks[BLOCK_ID]).not.toHaveProperty('binding');
    expect(s2._lastRejection?.type).toBe('UPDATE_BINDING');
  });
});
