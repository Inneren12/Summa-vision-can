export const getTranslations = jest.fn().mockImplementation((namespace: string) => {
  return Promise.resolve((key: string, params?: Record<string, unknown>) => {
    return `${namespace}.${key}`;
  });
});

export const getRequestConfig = jest.fn();
