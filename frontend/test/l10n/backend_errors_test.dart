import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:summa_vision_admin/l10n/backend_errors.dart';
import 'package:summa_vision_admin/l10n/generated/app_localizations.dart';

Future<(AppLocalizations, AppLocalizations)> _resolveLocalizations(
  WidgetTester tester,
) async {
  AppLocalizations? capturedEn;
  AppLocalizations? capturedRu;

  for (final locale in [const Locale('en'), const Locale('ru')]) {
    await tester.pumpWidget(
      MaterialApp(
        locale: locale,
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        home: Builder(
          builder: (ctx) {
            final l10n = AppLocalizations.of(ctx)!;
            if (locale.languageCode == 'en') capturedEn = l10n;
            if (locale.languageCode == 'ru') capturedRu = l10n;
            return const SizedBox.shrink();
          },
        ),
      ),
    );
    await tester.pump();
  }
  return (capturedEn!, capturedRu!);
}

void main() {
  testWidgets('maps CHART_EMPTY_DF to localized value in EN and RU',
      (tester) async {
    final (en, ru) = await _resolveLocalizations(tester);

    expect(mapBackendErrorCode('CHART_EMPTY_DF', en), 'No data to chart.');
    expect(
      mapBackendErrorCode('CHART_EMPTY_DF', ru),
      'Нет данных для построения графика.',
    );
  });

  testWidgets('maps CHART_INSUFFICIENT_COLUMNS in both locales',
      (tester) async {
    final (en, ru) = await _resolveLocalizations(tester);

    expect(
      mapBackendErrorCode('CHART_INSUFFICIENT_COLUMNS', en),
      'Not enough columns to build the chart.',
    );
    expect(
      mapBackendErrorCode('CHART_INSUFFICIENT_COLUMNS', ru),
      'Недостаточно столбцов для построения графика.',
    );
  });

  testWidgets('maps UNHANDLED_ERROR in both locales', (tester) async {
    final (en, ru) = await _resolveLocalizations(tester);

    expect(
      mapBackendErrorCode('UNHANDLED_ERROR', en),
      'Unexpected error while processing the job.',
    );
    expect(
      mapBackendErrorCode('UNHANDLED_ERROR', ru),
      'Непредвиденная ошибка при обработке задания.',
    );
  });

  testWidgets('maps COOL_DOWN_ACTIVE — Amendment 3 applied', (tester) async {
    final (en, ru) = await _resolveLocalizations(tester);

    expect(
      mapBackendErrorCode('COOL_DOWN_ACTIVE', en),
      'Please wait before starting another generation.',
    );
    expect(
      mapBackendErrorCode('COOL_DOWN_ACTIVE', ru),
      'Подождите перед повторной генерацией.',
    );
  });

  testWidgets('maps NO_HANDLER_REGISTERED in both locales', (tester) async {
    final (en, ru) = await _resolveLocalizations(tester);

    expect(mapBackendErrorCode('NO_HANDLER_REGISTERED', en), 'Unsupported operation.');
    expect(mapBackendErrorCode('NO_HANDLER_REGISTERED', ru), 'Операция не поддерживается.');
  });

  testWidgets('maps INCOMPATIBLE_PAYLOAD_VERSION — Amendment 4 applied',
      (tester) async {
    final (en, ru) = await _resolveLocalizations(tester);

    expect(
      mapBackendErrorCode('INCOMPATIBLE_PAYLOAD_VERSION', en),
      'Version mismatch between client and server payload.',
    );
    expect(
      mapBackendErrorCode('INCOMPATIBLE_PAYLOAD_VERSION', ru),
      'Несовместимая версия данных.',
    );
  });

  testWidgets('maps UNKNOWN_JOB_TYPE in both locales', (tester) async {
    final (en, ru) = await _resolveLocalizations(tester);

    expect(mapBackendErrorCode('UNKNOWN_JOB_TYPE', en), 'Unknown job type.');
    expect(mapBackendErrorCode('UNKNOWN_JOB_TYPE', ru), 'Неизвестный тип задания.');
  });

  testWidgets('returns null for unknown codes', (tester) async {
    final (en, _) = await _resolveLocalizations(tester);

    expect(mapBackendErrorCode('SOMETHING_ELSE', en), isNull);
  });

  testWidgets('returns null for null error code', (tester) async {
    final (en, _) = await _resolveLocalizations(tester);

    expect(mapBackendErrorCode(null, en), isNull);
  });
}
