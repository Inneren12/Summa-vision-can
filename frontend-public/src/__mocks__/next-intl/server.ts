/**
 * Test-time mock for `next-intl/server`.
 *
 * Contract: `getTranslations(namespace)` resolves a translator that maps
 * `key` → `"namespace.key"`. Tests should assert key identifiers, not
 * locale-rendered copy. Use real providers/messages only in explicit
 * locale-coupled integration tests; do not change this mock behavior.
 */
export const getTranslations = jest.fn().mockImplementation((namespace: string) => {
  return Promise.resolve((key: string, params?: Record<string, unknown>) => {
    return `${namespace}.${key}`;
  });
});

export const getRequestConfig = jest.fn();
