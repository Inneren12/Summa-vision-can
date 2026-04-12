'use client';

import { forwardRef, useEffect, useImperativeHandle, useRef } from 'react';

const TURNSTILE_SITE_KEY = process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY ?? '';

interface TurnstileWidgetProps {
  onSuccess: (token: string) => void;
  onError: () => void;
}

export interface TurnstileWidgetHandle {
  reset: () => void;
}

declare global {
  interface Window {
    turnstile?: {
      render: (
        container: HTMLElement,
        options: {
          sitekey: string;
          callback: (token: string) => void;
          'error-callback': () => void;
          'expired-callback': () => void;
          theme: string;
        },
      ) => string;
      reset: (widgetId: string) => void;
      remove: (widgetId: string) => void;
    };
    onTurnstileLoad?: () => void;
  }
}

const TurnstileWidget = forwardRef<TurnstileWidgetHandle, TurnstileWidgetProps>(
  function TurnstileWidget({ onSuccess, onError }, ref) {
    const containerRef = useRef<HTMLDivElement>(null);
    const widgetIdRef = useRef<string | null>(null);

    useImperativeHandle(ref, () => ({
      reset() {
        if (window.turnstile && widgetIdRef.current !== null) {
          window.turnstile.reset(widgetIdRef.current);
        }
      },
    }));

    useEffect(() => {
      if (!TURNSTILE_SITE_KEY) return;

      function renderWidget() {
        if (!containerRef.current || !window.turnstile) return;
        if (widgetIdRef.current !== null) return;

        widgetIdRef.current = window.turnstile.render(containerRef.current, {
          sitekey: TURNSTILE_SITE_KEY,
          callback: onSuccess,
          'error-callback': onError,
          'expired-callback': onError,
          theme: 'dark',
        });
      }

      // If turnstile is already loaded, render immediately
      if (window.turnstile) {
        renderWidget();
        return;
      }

      // Otherwise load the script
      const existingScript = document.querySelector(
        'script[src*="challenges.cloudflare.com/turnstile"]',
      );
      if (!existingScript) {
        window.onTurnstileLoad = renderWidget;
        const script = document.createElement('script');
        script.src =
          'https://challenges.cloudflare.com/turnstile/v0/api.js?onload=onTurnstileLoad';
        script.async = true;
        document.head.appendChild(script);
      } else {
        // Script exists but hasn't loaded yet
        window.onTurnstileLoad = renderWidget;
      }

      return () => {
        if (window.turnstile && widgetIdRef.current !== null) {
          window.turnstile.remove(widgetIdRef.current);
          widgetIdRef.current = null;
        }
      };
    }, [onSuccess, onError]);

    if (!TURNSTILE_SITE_KEY) {
      return null;
    }

    return (
      <div
        ref={containerRef}
        data-testid="turnstile-widget"
        className="flex justify-center"
      />
    );
  },
);

export default TurnstileWidget;
