'use client';

import { useLocale } from 'next-intl';
import { useRouter } from 'next/navigation';
import { useTransition } from 'react';

export function LanguageSwitcher() {
  const locale = useLocale();
  const router = useRouter();
  const [isPending, startTransition] = useTransition();

  function switchLocale(next: string) {
    document.cookie = `NEXT_LOCALE=${next}; path=/; max-age=31536000; SameSite=Lax`;
    startTransition(() => {
      router.refresh();
    });
  }

  return (
    <div className="flex items-center gap-1 text-sm">
      <button
        onClick={() => switchLocale('en')}
        disabled={locale === 'en' || isPending}
        className={locale === 'en' ? 'font-semibold' : 'opacity-50 hover:opacity-100'}
        aria-label="Switch to English"
      >
        EN
      </button>
      <span className="opacity-30">/</span>
      <button
        onClick={() => switchLocale('ru')}
        disabled={locale === 'ru' || isPending}
        className={locale === 'ru' ? 'font-semibold' : 'opacity-50 hover:opacity-100'}
        aria-label="Переключить на русский"
      >
        RU
      </button>
    </div>
  );
}
