import type { ValidationMessage } from './types';

type TranslatorFn = (key: string, params?: Record<string, unknown>) => string;

/**
 * Renders a ValidationMessage to a translated string.
 *
 * Contract: msg.key MUST start with "validation." (enforced by the ValidationMessageKey
 * type). The "validation." prefix is stripped because the caller already scoped their
 * translator to the "validation" namespace via useTranslations('validation').
 *
 * If a key does not start with "validation.", this is a programming error — the function
 * asserts in development and falls back to the raw key in production (so the UI does not
 * crash, but the issue is visible as an untranslated string).
 */
export function renderValidationMessage(
  msg: ValidationMessage,
  tValidation: TranslatorFn,
): string {
  const VALIDATION_PREFIX = 'validation.';

  if (!msg.key.startsWith(VALIDATION_PREFIX)) {
    if (process.env.NODE_ENV !== 'production') {
      throw new Error(
        `renderValidationMessage: expected key starting with "${VALIDATION_PREFIX}", got "${msg.key}"`,
      );
    }
    return msg.prefix ? `${msg.prefix}: ${msg.key}` : msg.key;
  }

  const keyWithoutNamespace = msg.key.slice(VALIDATION_PREFIX.length);
  const translated = tValidation(keyWithoutNamespace, msg.params ?? {});
  return msg.prefix ? `${msg.prefix}: ${translated}` : translated;
}
