import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:summa_vision_admin/l10n/generated/app_localizations.dart';

import 'app_bootstrap_state.dart';

/// Key used to persist the user-selected locale in SharedPreferences.
const String kLocaleStorageKey = 'selected_locale';

/// AsyncNotifier that owns locale resolution, persistence, and mutation.
///
/// Resolution order on startup:
///   1. Persisted locale in SharedPreferences (`selected_locale`) if valid
///   2. Device locale if in AppLocalizations.supportedLocales
///   3. Fallback to Locale('en')
///
/// Mutations via [setLocale] persist to SharedPreferences and update state
/// in one atomic transition.
///
/// This is the SINGLE ownership point for locale in the app. Do NOT resolve
/// locale independently in main.dart, router, or any other provider.
class AppBootstrapNotifier extends AsyncNotifier<AppBootstrapState> {
  @override
  Future<AppBootstrapState> build() async {
    final prefs = await SharedPreferences.getInstance();
    final locale = _resolveLocale(prefs);
    return AppBootstrapState(locale: locale);
  }

  Locale _resolveLocale(SharedPreferences prefs) {
    final persisted = prefs.getString(kLocaleStorageKey);
    if (persisted != null) {
      final locale = Locale(persisted);
      if (_isSupported(locale)) {
        return locale;
      }
    }

    final deviceLocales = WidgetsBinding.instance.platformDispatcher.locales;
    for (final deviceLocale in deviceLocales) {
      final normalized = Locale(deviceLocale.languageCode);
      if (_isSupported(normalized)) {
        return normalized;
      }
    }

    return const Locale('en');
  }

  bool _isSupported(Locale locale) {
    return AppLocalizations.supportedLocales.any(
      (supported) => supported.languageCode == locale.languageCode,
    );
  }

  /// Change the active locale and persist the choice.
  ///
  /// Callers: only the language switcher UI. Do NOT call from other places.
  Future<void> setLocale(Locale newLocale) async {
    if (!_isSupported(newLocale)) {
      throw ArgumentError(
        'Locale ${newLocale.languageCode} is not in '
        'AppLocalizations.supportedLocales',
      );
    }

    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(kLocaleStorageKey, newLocale.languageCode);

    state = AsyncValue.data(
      (state.valueOrNull ?? AppBootstrapState(locale: newLocale)).copyWith(
        locale: newLocale,
      ),
    );
  }
}

/// Top-level AsyncNotifierProvider for app bootstrap state.
final appBootstrapProvider =
    AsyncNotifierProvider<AppBootstrapNotifier, AppBootstrapState>(
  AppBootstrapNotifier.new,
);
