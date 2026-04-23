/**
 * Test-time mock for next-intl.
 *
 * Contract: `useTranslations(namespace)` returns a function that maps
 * `key` → string `"namespace.key"`. This is intentional: tests assert on
 * stable key identifiers, not on locale-specific strings. Translation
 * correctness (EN/RU values) is verified separately via integration tests
 * or manual QA, not via unit-test assertions.
 *
 * If you are adding new tests: assert on `"namespace.key"` format, not on
 * literal English or Russian strings. If you need locale-coupled tests,
 * wrap the component under test in `NextIntlClientProvider` with real
 * messages in that specific test file — do not change this mock.
 */
export const useTranslations = jest.fn().mockImplementation((namespace: string) => {
  return (key: string, params?: Record<string, unknown>) => `${namespace}.${key}`;
});

export const useLocale = jest.fn().mockReturnValue('en');
export const useFormatter = jest.fn();
export const NextIntlClientProvider = ({ children }: { children: React.ReactNode }) => children;
