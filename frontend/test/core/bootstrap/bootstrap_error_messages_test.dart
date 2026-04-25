import 'dart:ui';

import 'package:flutter_test/flutter_test.dart';
import 'package:summa_vision_admin/core/bootstrap/bootstrap_error_messages.dart';

void main() {
  group('bootstrapErrorMessage', () {
    test('returns RU message for ru locale', () {
      final result = bootstrapErrorMessage(
        Exception('boom'),
        localeProvider: () => const Locale('ru'),
      );
      expect(result, contains('Не удалось запустить приложение'));
      expect(result, contains('boom'));
    });

    test('returns EN message for en locale', () {
      final result = bootstrapErrorMessage(
        Exception('boom'),
        localeProvider: () => const Locale('en'),
      );
      expect(result, contains('App bootstrap failed'));
    });

    test('falls back to EN for unsupported locale (e.g. fr)', () {
      final result = bootstrapErrorMessage(
        Exception('boom'),
        localeProvider: () => const Locale('fr'),
      );
      expect(result, contains('App bootstrap failed'));
    });

    test('matches RU for ru-RU country variant', () {
      // languageCode is 'ru' regardless of country — should still match RU.
      final result = bootstrapErrorMessage(
        Exception('boom'),
        localeProvider: () => const Locale('ru', 'RU'),
      );
      expect(result, contains('Не удалось запустить приложение'));
    });

    test('appends error string', () {
      final err = StateError('container init failed');
      final result = bootstrapErrorMessage(
        err,
        localeProvider: () => const Locale('en'),
      );
      expect(result, contains('container init failed'));
    });
  });
}
