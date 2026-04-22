export const useTranslations = jest.fn().mockImplementation((namespace: string) => {
  return (key: string, params?: Record<string, unknown>) => `${namespace}.${key}`;
});

export const useLocale = jest.fn().mockReturnValue('en');
export const useFormatter = jest.fn();
export const NextIntlClientProvider = ({ children }: { children: React.ReactNode }) => children;
