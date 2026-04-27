'use client';

import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { useTranslations } from 'next-intl';
import { TK } from '../config/tokens';
import { BREG } from '../registry/blocks';
import type { Block } from '../types';

export interface BlockContextMenuProps {
  block: Block;
  position: { x: number; y: number };
  onClose: () => void;
  onLock: () => void;
  onHide: () => void;
  onDuplicate: () => void;
  onDelete: () => void;
  // Mode-axis flag — design mode permits structural mutations; in template
  // mode duplicate/delete are greyed out. Lock/hide remain available.
  designMode: boolean;
}

const MENU_MARGIN = 8;

interface ItemDescriptor {
  testid: string;
  label: string;
  shortcut: string;
  onClick: () => void;
  disabled: boolean;
  disabledTitle?: string;
}

export function BlockContextMenu({
  block,
  position,
  onClose,
  onLock,
  onHide,
  onDuplicate,
  onDelete,
  designMode,
}: BlockContextMenuProps) {
  const t = useTranslations('editor.context_menu');
  const ref = useRef<HTMLDivElement | null>(null);
  const [adjusted, setAdjusted] = useState<{ x: number; y: number }>(position);
  const [mounted, setMounted] = useState<boolean>(false);

  // SSR / jsdom safety: only mount the portal on the client.
  useEffect(() => {
    setMounted(true);
  }, []);

  // Auto-close handlers — Escape, click outside, scroll.
  useEffect(() => {
    const onPointerDown = (e: PointerEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        onClose();
      }
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
      }
    };
    const onScroll = () => onClose();
    document.addEventListener('pointerdown', onPointerDown);
    document.addEventListener('keydown', onKey);
    document.addEventListener('scroll', onScroll, true);
    return () => {
      document.removeEventListener('pointerdown', onPointerDown);
      document.removeEventListener('keydown', onKey);
      document.removeEventListener('scroll', onScroll, true);
    };
  }, [onClose]);

  // Reposition into viewport after first paint so the menu never spills off
  // the screen edge when opened near the bottom-right corner.
  useLayoutEffect(() => {
    if (!ref.current) return;
    const rect = ref.current.getBoundingClientRect();
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    let x = position.x;
    let y = position.y;
    if (x + rect.width + MENU_MARGIN > vw) x = Math.max(MENU_MARGIN, vw - rect.width - MENU_MARGIN);
    if (y + rect.height + MENU_MARGIN > vh) y = Math.max(MENU_MARGIN, vh - rect.height - MENU_MARGIN);
    if (x !== adjusted.x || y !== adjusted.y) setAdjusted({ x, y });
    // Run only when the requested position changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [position.x, position.y]);

  if (!mounted || typeof document === 'undefined') return null;

  const isLocked = block.locked === true;
  const isHidden = block.visible === false;
  const reg = BREG[block.type];
  // Template-immutable status: required_locked / required_editable blocks
  // cannot be deleted from the document. Mirrors the reducer enforcement
  // in REMOVE_BLOCK.
  const templateRequired =
    reg?.status === 'required_locked' || reg?.status === 'required_editable';
  // maxPerSection is enforced inside the reducer; no per-menu pre-check
  // here because the menu has no section context to count against. The
  // reducer's withRejection path covers the edge case.

  const items: ItemDescriptor[] = [
    {
      testid: 'ctx-lock',
      label: isLocked ? t('unlock') : t('lock'),
      shortcut: '⌘L',
      onClick: () => {
        onLock();
        onClose();
      },
      disabled: false,
    },
    {
      testid: 'ctx-hide',
      label: isHidden ? t('show') : t('hide'),
      shortcut: '⌘H',
      onClick: () => {
        onHide();
        onClose();
      },
      // Hide requires unlocked block. The menu still renders the item but
      // disables it so the operator sees the cause.
      disabled: isLocked,
      disabledTitle: isLocked ? t('hide_disabled_locked') : undefined,
    },
    {
      testid: 'ctx-duplicate',
      label: t('duplicate'),
      shortcut: '⌘D',
      onClick: () => {
        onDuplicate();
        onClose();
      },
      disabled: !designMode,
      disabledTitle: !designMode ? t('disabled_template_mode') : undefined,
    },
    {
      testid: 'ctx-delete',
      label: t('delete'),
      shortcut: 'Delete',
      onClick: () => {
        onDelete();
        onClose();
      },
      disabled: templateRequired || !designMode,
      disabledTitle: templateRequired
        ? t('delete_disabled_template_locked')
        : !designMode
          ? t('disabled_template_mode')
          : undefined,
    },
  ];

  return createPortal(
    <div
      ref={ref}
      role="menu"
      aria-label={t('aria_label')}
      data-testid="block-context-menu"
      style={{
        position: 'fixed',
        left: adjusted.x,
        top: adjusted.y,
        zIndex: 100,
        minWidth: '200px',
        background: TK.c.bgSurf,
        border: `1px solid ${TK.c.brd}`,
        borderRadius: '4px',
        padding: '4px 0',
        boxShadow: '0 12px 32px rgba(0,0,0,0.5)',
        fontFamily: TK.font.body,
        fontSize: '12px',
        color: TK.c.txtP,
      }}
    >
      {items.map((item) => (
        <button
          key={item.testid}
          type="button"
          role="menuitem"
          data-testid={item.testid}
          onClick={item.onClick}
          disabled={item.disabled}
          title={item.disabledTitle}
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '24px',
            width: '100%',
            padding: '6px 12px',
            background: 'transparent',
            border: 'none',
            color: item.disabled ? TK.c.txtM : TK.c.txtP,
            fontFamily: TK.font.body,
            fontSize: '12px',
            textAlign: 'left',
            cursor: item.disabled ? 'not-allowed' : 'pointer',
          }}
          onMouseEnter={(e) => {
            if (!item.disabled) e.currentTarget.style.background = TK.c.bgHov;
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = 'transparent';
          }}
        >
          <span>{item.label}</span>
          <span
            style={{
              fontFamily: TK.font.data,
              fontSize: '10px',
              color: TK.c.txtM,
              letterSpacing: '0.3px',
            }}
          >
            {item.shortcut}
          </span>
        </button>
      ))}
    </div>,
    document.body,
  );
}
