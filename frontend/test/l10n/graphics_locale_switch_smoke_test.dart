import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:summa_vision_admin/core/shell/language_switcher.dart';
import 'package:summa_vision_admin/features/graphics/application/chart_config_notifier.dart';
import 'package:summa_vision_admin/features/graphics/application/generation_state_notifier.dart';
import 'package:summa_vision_admin/features/graphics/presentation/chart_config_screen.dart';

import '../helpers/pump_localized_router.dart';

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

    await pumpLocalizedRouter(
      tester,
      home: Scaffold(
        appBar: AppBar(actions: const [LanguageSwitcher()]),
        body: const ChartConfigScreen(
          storageKey: 'statcan/processed/13-10-0888-01/data.parquet',
        ),
      ),
      overrides: [
        chartConfigNotifierProvider.overrideWith(
          () => _MockChartConfigNotifier(config),
        ),
        chartGenerationNotifierProvider.overrideWith(
          () => _MockGenerationNotifier(const ChartGenerationState()),
        ),
      ],
    );

    final enTitle = l10n(tester).chartConfigAppBarTitle;
    final enDataset = l10n(tester).chartConfigDatasetLabel;
    final enBackground = l10n(tester).chartConfigBackgroundCategoryLabel;

    expect(find.text(enTitle), findsOneWidget);
    expect(find.text(enDataset), findsOneWidget);
    expect(find.text(enBackground), findsOneWidget);

    await switchLocaleVia(tester, 'ru');

    expect(find.text(l10n(tester).chartConfigAppBarTitle), findsAtLeastNWidgets(1));
    expect(find.text(l10n(tester).chartConfigDatasetLabel), findsAtLeastNWidgets(1));
    expect(
      find.text(l10n(tester).chartConfigBackgroundCategoryLabel),
      findsAtLeastNWidgets(1),
    );

    expect(find.text(enTitle), findsNothing);
    expect(find.text(enDataset), findsNothing);
    expect(find.text(enBackground), findsNothing);
  });
}
