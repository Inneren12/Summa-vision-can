import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:summa_vision_admin/core/app_bootstrap/app_bootstrap_provider.dart';
import 'package:summa_vision_admin/core/shell/language_switcher.dart';
import 'package:summa_vision_admin/core/theme/app_theme.dart';
import 'package:summa_vision_admin/features/graphics/application/chart_config_notifier.dart';
import 'package:summa_vision_admin/features/graphics/application/generation_state_notifier.dart';
import 'package:summa_vision_admin/features/graphics/presentation/chart_config_screen.dart';
import 'package:summa_vision_admin/l10n/generated/app_localizations.dart';

class _MockChartConfigNotifier extends ChartConfigNotifier {
  _MockChartConfigNotifier(this._initial);
  final ChartConfig _initial;

  @override
  ChartConfig build() => _initial;
}

class _MockGenerationNotifier extends ChartGenerationNotifier {
  _MockGenerationNotifier(this._initial);
  final ChartGenerationState _initial;

  @override
  ChartGenerationState build() => _initial;

  @override
  Future<void> generate(request) async {}
}

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets('ChartConfigScreen chrome rerenders after EN -> RU switch',
      (tester) async {
    const config = ChartConfig(
      dataKey: 'statcan/processed/13-10-0888-01/data.parquet',
      title: 'Smoke Title',
    );

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          chartConfigNotifierProvider.overrideWith(
            () => _MockChartConfigNotifier(config),
          ),
          chartGenerationNotifierProvider.overrideWith(
            () => _MockGenerationNotifier(const ChartGenerationState()),
          ),
        ],
        child: Consumer(
          builder: (context, ref, _) {
            final bootstrap = ref.watch(appBootstrapProvider);
            return MaterialApp(
              theme: AppTheme.dark,
              locale: bootstrap.when(
                data: (state) => state.locale,
                loading: () => const Locale('en'),
                error: (_, __) => const Locale('en'),
              ),
              supportedLocales: AppLocalizations.supportedLocales,
              localizationsDelegates: AppLocalizations.localizationsDelegates,
              home: Scaffold(
                appBar: AppBar(actions: const [LanguageSwitcher()]),
                body: const ChartConfigScreen(
                  storageKey: 'statcan/processed/13-10-0888-01/data.parquet',
                ),
              ),
            );
          },
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Chart Configuration'), findsOneWidget);
    expect(find.text('Dataset'), findsOneWidget);
    expect(find.text('Background Category'), findsOneWidget);

    final russianButton = find.widgetWithText(
      TextButton,
      'Russian',
      skipOffstage: false,
    );
    expect(russianButton, findsOneWidget);
    await tester.tap(russianButton);
    await tester.pumpAndSettle();

    expect(find.text('Настройка графика'), findsAtLeastNWidgets(1));
    expect(find.text('Набор данных'), findsAtLeastNWidgets(1));
    expect(find.text('Категория фона'), findsAtLeastNWidgets(1));
  });
}
