import { getTranslations } from 'next-intl/server';
import Link from 'next/link';
import { LanguageSwitcher } from '@/components/admin/LanguageSwitcher';

export async function generateMetadata() {
  const t = await getTranslations('admin');

  return {
    title: t('meta.title'),
    robots: { index: false, follow: false },
  };
}

export default async function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const t = await getTranslations('admin');

  return (
    <div className="min-h-screen bg-bg-app text-text-primary">
      <header className="border-b border-border-default bg-bg-surface">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link href="/admin" className="font-display text-lg font-semibold">
            {t('header.brand')}
          </Link>
          <div className="flex items-center gap-3">
            <span className="text-sm text-text-secondary">{t('header.internal_tool')}</span>
            <LanguageSwitcher />
          </div>
        </div>
      </header>
      <main className="max-w-6xl mx-auto px-6 py-8">{children}</main>
    </div>
  );
}
