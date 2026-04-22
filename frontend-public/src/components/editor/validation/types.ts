export type ValidationMessageKey = string;

export type ValidationMessageParams = Record<string, string | number | undefined>;

export interface ValidationMessage {
  key: ValidationMessageKey;
  params?: ValidationMessageParams;
}

// Backward-compat helper for tests and debug overlay that may log raw messages.
// Produces a human-readable string from a ValidationMessage — EN only.
// Do NOT use this in production UI paths.
export function formatValidationMessageDev(msg: ValidationMessage): string {
  const paramStr = msg.params
    ? Object.entries(msg.params).map(([k, v]) => `${k}=${v}`).join(', ')
    : '';
  return paramStr ? `${msg.key} (${paramStr})` : msg.key;
}
