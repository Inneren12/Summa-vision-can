/**
 * Template literal type ensures every ValidationMessage key starts with `validation.`.
 * This is a weak-but-useful guard: it catches typos like `validtion.*` at compile time.
 */
export type ValidationMessageKey = `validation.${string}`;

export type ValidationMessageParams = Record<string, string | number | undefined>;

export interface ValidationMessage {
  key: ValidationMessageKey;
  params?: ValidationMessageParams;
  /** Optional literal prefix rendered BEFORE the translated message (e.g. block name).
   *  Used for wrapping child validation errors with parent block context without
   *  losing child-message localization. */
  prefix?: string;
}

// Backward-compat helper for tests and debug overlay that may log raw messages.
// Produces a human-readable string from a ValidationMessage — EN only.
// Do NOT use this in production UI paths.
export function formatValidationMessageDev(msg: ValidationMessage): string {
  const paramStr = msg.params
    ? Object.entries(msg.params).map(([k, v]) => `${k}=${v}`).join(', ')
    : '';
  const body = paramStr ? `${msg.key} (${paramStr})` : msg.key;
  return msg.prefix ? `${msg.prefix}: ${body}` : body;
}
