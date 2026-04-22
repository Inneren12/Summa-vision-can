import type { ValidationMessage } from './types';

type TranslatorFn = (key: string, params?: Record<string, unknown>) => string;

/**
 * Renders a ValidationMessage to a translated string.
 * The `tValidation` translator should be obtained via
 * `useTranslations('validation')` in the calling component.
 *
 * Strips the "validation." prefix from the key before passing to the
 * translator, because the caller already scoped to the "validation" namespace.
 */
export function renderValidationMessage(
  msg: ValidationMessage,
  tValidation: TranslatorFn,
): string {
  const keyWithoutNamespace = msg.key.replace(/^validation\./, '');
  const translated = tValidation(keyWithoutNamespace, msg.params ?? {});
  return msg.prefix ? `${msg.prefix}: ${translated}` : translated;
}
