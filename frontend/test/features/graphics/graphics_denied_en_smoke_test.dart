import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
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

Widget _harness({
  required ChartConfig config,
  required ChartGenerationState genState,
}) {
  return ProviderScope(
    overrides: [
      chartConfigNotifierProvider.overrideWith(
        () => _MockChartConfigNotifier(config),
      ),
      chartGenerationNotifierProvider.overrideWith(
        () => _MockGenerationNotifier(genState),
      ),
    ],
    child: MaterialApp(
      theme: AppTheme.dark,
      locale: const Locale('ru'),
      supportedLocales: AppLocalizations.supportedLocales,
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      home: const ChartConfigScreen(
        storageKey: 'statcan/processed/13-10-0888-01/data.parquet',
      ),
    ),
  );
}

void main() {
  testWidgets('RU chart config denies EN literals in config form', (tester) async {
    await tester.pumpWidget(
      _harness(
        config: const ChartConfig(
          dataKey: 'statcan/processed/13-10-0888-01/data.parquet',
          title: 'RU smoke',
          sourceProductId: '13-10-0888-01',
        ),
        genState: const ChartGenerationState(),
      ),
    );
    await tester.pumpAndSettle();

    // Denied EN literals (migrated, must NOT appear when locale is ru)
    expect(find.text('Chart Configuration', skipOffstage: false), findsNothing);
    expect(find.text('StatCan Cube', skipOffstage: false), findsNothing);
    expect(find.text('Upload Data', skipOffstage: false), findsNothing);
    expect(find.text('Dataset', skipOffstage: false), findsNothing);
    expect(find.text('Size Preset', skipOffstage: false), findsNothing);
    expect(find.text('Background Category', skipOffstage: false), findsNothing);
    expect(find.text('Chart Headline', skipOffstage: false), findsNothing);
    expect(find.text('Generate Graphic', skipOffstage: false), findsNothing);
    expect(find.text('Chart Type', skipOffstage: false), findsNothing);
    expect(find.text('Housing', skipOffstage: false), findsNothing);
    expect(find.text('Inflation', skipOffstage: false), findsNothing);
    expect(find.text('Employment', skipOffstage: false), findsNothing);
    expect(find.text('Trade', skipOffstage: false), findsNothing);
    expect(find.text('Energy', skipOffstage: false), findsNothing);
    expect(find.text('Demographics', skipOffstage: false), findsNothing);

    // Allowlist (Category D): ChartType and SizePreset values stay EN
    expect(
      find.textContaining('Line Chart', skipOffstage: false),
      findsAtLeastNWidgets(1),
    );
    expect(
      find.textContaining('Instagram', skipOffstage: false),
      findsAtLeastNWidgets(1),
    );
  });

  testWidgets('RU chart config polling state denies EN status', (tester) async {
    await tester.pumpWidget(
      _harness(
        config: const ChartConfig(
          dataKey: 'statcan/processed/13-10-0888-01/data.parquet',
          title: 'x',
        ),
        genState: const ChartGenerationState(
          phase: GenerationPhase.polling,
          pollCount: 5,
        ),
      ),
    );
    await tester.pump();

    expect(find.textContaining('Generating graphic', skipOffstage: false), findsNothing);
    expect(find.textContaining('Estimated time remaining', skipOffstage: false), findsNothing);
  });

  testWidgets('RU chart config timeout denies EN timeout literal', (tester) async {
    await tester.pumpWidget(
      _harness(
        config: const ChartConfig(
          dataKey: 'statcan/processed/13-10-0888-01/data.parquet',
          title: 'x',
        ),
        genState: const ChartGenerationState(phase: GenerationPhase.timeout),
      ),
    );
    await tester.pump();

    expect(find.textContaining('timed out', skipOffstage: false), findsNothing);
    expect(find.text('Try Again', skipOffstage: false), findsNothing);
    expect(find.text('Retry', skipOffstage: false), findsNothing);
  });
}
