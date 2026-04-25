import 'dart:ui' show PlatformDispatcher;

/// Returns a locale-aware bootstrap error message.
///
/// Picks RU translation when [PlatformDispatcher.instance.locale.languageCode]
/// is `'ru'`. Defaults to EN for any other locale (including unsupported ones).
///
/// This is a pre-localization fallback used ONLY before the
/// generated localization bundle is available (e.g., during Riverpod
/// container init failure). All in-app errors must continue to use
/// AppLocalizations.
String bootstrapErrorMessage(Object error, {PlatformDispatcher? dispatcher}) {
  final d = dispatcher ?? PlatformDispatcher.instance;
  final code = d.locale.languageCode;
  final localized =
      _bootstrapErrorMessages[code] ?? _bootstrapErrorMessages['en']!;
  return '$localized: $error';
}

const Map<String, String> _bootstrapErrorMessages = {
  'en': 'App bootstrap failed',
  'ru': 'Не удалось запустить приложение',
};
