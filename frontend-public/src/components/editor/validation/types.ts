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

/**
 * Dev/debug/test-only validation message formatter. Produces EN debug strings like
 * `validation.items.too_many (count=31, max=30)` for log lines and import-guard error text.
 *
 * Do NOT use in user-facing UI — use `renderValidationMessage` with a translator instead.
 */
export function formatValidationMessageDev(msg: ValidationMessage): string {
  const paramStr = msg.params
    ? Object.entries(msg.params).map(([k, v]) => `${k}=${v}`).join(', ')
    : '';
  const body = paramStr ? `${msg.key} (${paramStr})` : msg.key;
  return msg.prefix ? `${msg.prefix}: ${body}` : body;
}
