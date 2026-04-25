import 'dart:ui' show Locale, PlatformDispatcher;

/// Returns the current platform locale.
///
/// Default [LocaleProvider] used by [bootstrapErrorMessage]. Read directly
/// from the platform locale so tests can override the provider directly.
Locale _platformLocale() => PlatformDispatcher.instance.locale;

/// Resolves the locale used by [bootstrapErrorMessage].
///
/// Tests inject a fixed locale via this typedef — much simpler than faking
/// engine dispatcher interface, which is large and unstable across SDK upgrades.
typedef LocaleProvider = Locale Function();

/// Returns a locale-aware bootstrap error message.
///
/// Picks RU translation when [LocaleProvider] returns a [Locale] whose
/// `languageCode` is `'ru'`. Defaults to EN for any other locale (including
/// unsupported ones).
///
/// This is a pre-localization fallback used ONLY before the
/// [AppLocalizations] generated bundle is available (e.g., during Riverpod
/// container init failure). All in-app errors must continue to use
/// `AppLocalizations.of(context)`.
String bootstrapErrorMessage(
  Object error, {
  LocaleProvider localeProvider = _platformLocale,
}) {
  final code = localeProvider().languageCode;
  final localized =
      _bootstrapErrorMessages[code] ?? _bootstrapErrorMessages['en']!;
  return '$localized: $error';
}

const Map<String, String> _bootstrapErrorMessages = {
  'en': 'App bootstrap failed',
  'ru': 'Не удалось запустить приложение',
};
