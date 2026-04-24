import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:summa_vision_admin/features/graphics/application/chart_config_notifier.dart';
import 'package:summa_vision_admin/features/graphics/application/generation_state_notifier.dart';
import 'package:summa_vision_admin/features/graphics/domain/chart_constants.dart';
import 'package:summa_vision_admin/features/graphics/domain/generation_result.dart';
import 'package:summa_vision_admin/features/graphics/presentation/chart_config_screen.dart';
import 'package:summa_vision_admin/l10n/generated/app_localizations.dart';

import '../../../helpers/localized_pump.dart';

// ---------------------------------------------------------------------------
// Mock Notifiers
// ---------------------------------------------------------------------------

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
  Future<void> generate(request) async {
    // no-op in tests
  }
}

// ---------------------------------------------------------------------------
// Helper: pump screen with overrides through localized harness
// ---------------------------------------------------------------------------

Future<void> _pumpScreen(
  WidgetTester tester, {
  ChartConfig? config,
  ChartGenerationState? genState,
  String storageKey = 'statcan/processed/13-10-0888-01/2024-12-15.parquet',
  String? productId,
}) {
  final effectiveConfig = config ??
      ChartConfig(
        dataKey: storageKey,
        sourceProductId: productId,
        title: 'Test Headline',
      );
  final effectiveGenState = genState ?? const ChartGenerationState();

  return pumpLocalizedWidget(
    tester,
    ChartConfigScreen(
      storageKey: storageKey,
      productId: productId,
    ),
    overrides: [
      chartConfigNotifierProvider.overrideWith(
        () => _MockChartConfigNotifier(effectiveConfig),
      ),
      chartGenerationNotifierProvider.overrideWith(
        () => _MockGenerationNotifier(effectiveGenState),
      ),
    ],
  );
}

AppLocalizations _l10n(WidgetTester tester) {
  final ctx = tester.element(find.byType(ChartConfigScreen));
  return AppLocalizations.of(ctx)!;
}

void main() {
  group('ChartConfigScreen — renders all controls', () {
    testWidgets('test_chart_config_screen_renders_all_controls', (tester) async {
      await _pumpScreen(tester);
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('chart_type_selector')), findsOneWidget);
      expect(find.byKey(const Key('size_preset_selector')), findsOneWidget);
      expect(find.byKey(const Key('category_chip_housing')), findsOneWidget);
      expect(find.byKey(const Key('category_chip_inflation')), findsOneWidget);
      expect(find.byKey(const Key('category_chip_employment')), findsOneWidget);
      expect(find.byKey(const Key('category_chip_trade')), findsOneWidget);
      expect(find.byKey(const Key('category_chip_energy')), findsOneWidget);
      expect(find.byKey(const Key('category_chip_demographics')), findsOneWidget);
      expect(find.byKey(const Key('title_field')), findsOneWidget);
      expect(find.byKey(const Key('generate_button')), findsOneWidget);
    });
  });

  group('ChartConfigScreen — chart type selection', () {
    testWidgets('test_chart_type_selection_updates_state', (tester) async {
      await _pumpScreen(tester);
      await tester.pumpAndSettle();

      await tester.tap(find.byKey(const Key('chart_type_selector')));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Bar Chart').last);
      await tester.pumpAndSettle();

      expect(find.text('Bar Chart'), findsOneWidget);
    });
  });

  group('ChartConfigScreen — size preset selection', () {
    testWidgets('test_size_preset_selection', (tester) async {
      await _pumpScreen(tester);
      await tester.pumpAndSettle();

      expect(find.text('Twitter / X (1.91:1)'), findsOneWidget);
      await tester.tap(find.text('Twitter / X (1.91:1)'));
      await tester.pumpAndSettle();
    });
  });

  group('ChartConfigScreen — category selection', () {
    testWidgets('test_category_selection', (tester) async {
      await _pumpScreen(tester);
      await tester.pumpAndSettle();

      await tester.tap(find.byKey(const Key('category_chip_inflation')));
      await tester.pumpAndSettle();
    });
  });

  group('ChartConfigScreen — generate button disabled when title empty', () {
    testWidgets('test_generate_button_disabled_when_title_empty',
        (tester) async {
      await _pumpScreen(
        tester,
        config: const ChartConfig(
          dataKey: 'statcan/processed/13-10-0888-01/2024-12-15.parquet',
          title: '',
        ),
      );
      await tester.pumpAndSettle();

      final button = tester.widget<ElevatedButton>(
        find.byKey(const Key('generate_button')),
      );
      expect(button.onPressed, isNull);
    });

    testWidgets('button is enabled when title is non-empty', (tester) async {
      await _pumpScreen(
        tester,
        config: const ChartConfig(
          dataKey: 'statcan/processed/13-10-0888-01/2024-12-15.parquet',
          title: 'Housing Price Index',
        ),
      );
      await tester.pumpAndSettle();

      final button = tester.widget<ElevatedButton>(
        find.byKey(const Key('generate_button')),
      );
      expect(button.onPressed, isNotNull);
    });
  });

  group('ChartConfigScreen — submitting phase', () {
    testWidgets('test_generation_submitting_shows_spinner', (tester) async {
      await _pumpScreen(
        tester,
        genState: const ChartGenerationState(
          phase: GenerationPhase.submitting,
        ),
      );
      await tester.pump();

      final l10n = _l10n(tester);
      expect(find.byType(CircularProgressIndicator), findsOneWidget);
      expect(find.text(l10n.generationStatusSubmitting), findsOneWidget);
    });
  });

  group('ChartConfigScreen — polling phase', () {
    testWidgets('test_generation_polling_shows_progress', (tester) async {
      await _pumpScreen(
        tester,
        genState: const ChartGenerationState(
          phase: GenerationPhase.polling,
          jobId: 'mock-gen-job-789',
          pollCount: 15,
        ),
      );
      await tester.pump();

      final l10n = _l10n(tester);
      expect(
        find.text(l10n.generationStatusPolling(15, ChartGenerationNotifier.maxPolls)),
        findsOneWidget,
      );
      expect(find.byType(LinearProgressIndicator), findsOneWidget);
      expect(
        find.text(l10n.chartConfigEtaRemaining(
          (ChartGenerationNotifier.maxPolls - 15) * 2,
        )),
        findsOneWidget,
      );
    });
  });

  group('ChartConfigScreen — success phase', () {
    testWidgets('test_generation_success_shows_image', (tester) async {
      await _pumpScreen(
        tester,
        genState: const ChartGenerationState(
          phase: GenerationPhase.success,
          result: GenerationResult(
            publicationId: 42,
            cdnUrlLowres:
                'https://placehold.co/1080x1080/141414/00E5FF?text=Mock+Chart',
            s3KeyHighres: 'publications/42/v1/abcd_highres.png',
            version: 1,
          ),
        ),
      );
      await tester.pump();

      expect(find.byKey(const Key('download_button')), findsOneWidget);
      expect(find.byKey(const Key('generate_another_button')), findsOneWidget);
      expect(find.byKey(const Key('back_to_preview_button')), findsOneWidget);
      final l10n = _l10n(tester);
      expect(find.text(l10n.chartConfigPublicationChip(42)), findsOneWidget);
      expect(find.text(l10n.chartConfigVersionChip('1')), findsOneWidget);
    });
  });

  group('ChartConfigScreen — timeout phase', () {
    testWidgets('test_generation_timeout_shows_retry', (tester) async {
      await _pumpScreen(
        tester,
        genState: const ChartGenerationState(
          phase: GenerationPhase.timeout,
        ),
      );
      await tester.pump();

      final l10n = _l10n(tester);
      expect(find.text(l10n.generationStatusTimeout), findsOneWidget);
      expect(find.byKey(const Key('retry_button')), findsOneWidget);
    });
  });

  group('ChartConfigScreen — failed phase', () {
    testWidgets('test_generation_failed_shows_error', (tester) async {
      await _pumpScreen(
        tester,
        genState: const ChartGenerationState(
          phase: GenerationPhase.failed,
          errorMessage: 'Backend returned 500',
        ),
      );
      await tester.pump();

      expect(find.textContaining('Backend returned 500'), findsOneWidget);
      expect(find.byKey(const Key('retry_button')), findsOneWidget);
    });
  });

  group('ChartConfigScreen — generate another resets state', () {
    testWidgets('test_generate_another_resets_state', (tester) async {
      await _pumpScreen(
        tester,
        genState: const ChartGenerationState(
          phase: GenerationPhase.success,
          result: GenerationResult(
            publicationId: 1,
            cdnUrlLowres:
                'https://placehold.co/1080x1080/141414/00E5FF?text=Mock+Chart',
            s3KeyHighres: 'publications/1/v1/abcd_highres.png',
            version: 1,
          ),
        ),
      );
      await tester.pump();

      expect(find.byKey(const Key('generate_another_button')), findsOneWidget);
      await tester.tap(find.byKey(const Key('generate_another_button')));
      await tester.pumpAndSettle();
    });
  });

  group('ChartConfigScreen — result cached across navigation', () {
    testWidgets('test_result_cached_across_navigation', (tester) async {
      final container = ProviderContainer(
        overrides: [
          chartGenerationNotifierProvider.overrideWith(
            () => _MockGenerationNotifier(
              const ChartGenerationState(
                phase: GenerationPhase.success,
                result: GenerationResult(
                  publicationId: 1,
                  cdnUrlLowres:
                      'https://placehold.co/1080x1080/141414/00E5FF?text=Mock+Chart',
                  s3KeyHighres: 'publications/1/v1/abcd_highres.png',
                  version: 1,
                ),
              ),
            ),
          ),
        ],
      );
      addTearDown(container.dispose);

      final state = container.read(chartGenerationNotifierProvider);
      expect(state.phase, GenerationPhase.success);
      expect(state.result, isNotNull);
      expect(state.result!.publicationId, 1);

      final stateAfter = container.read(chartGenerationNotifierProvider);
      expect(stateAfter.phase, GenerationPhase.success);
    });
  });

  group('ChartGenerationNotifier unit tests', () {
    test('initial state is idle', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      final state = container.read(chartGenerationNotifierProvider);
      expect(state.phase, GenerationPhase.idle);
      expect(state.pollCount, 0);
      expect(state.result, isNull);
      expect(state.jobId, isNull);
    });

    test('maxPolls is 60', () {
      expect(ChartGenerationNotifier.maxPolls, 60);
    });

    test('reset() returns to idle state', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      container.read(chartGenerationNotifierProvider.notifier).reset();
      final state = container.read(chartGenerationNotifierProvider);
      expect(state.phase, GenerationPhase.idle);
      expect(state.pollCount, 0);
    });
  });

  group('Dataset switching resets state', () {
    test('switching dataset resets generation state', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      final genNotifier =
          container.read(chartGenerationNotifierProvider.notifier);
      final configNotifier =
          container.read(chartConfigNotifierProvider.notifier);

      configNotifier.setDataKey('datasetA/file.parquet', productId: 'A');
      expect(container.read(chartConfigNotifierProvider).dataKey,
          'datasetA/file.parquet');

      configNotifier.reset('datasetB/file.parquet', sourceProductId: 'B');
      genNotifier.reset();

      final genState = container.read(chartGenerationNotifierProvider);
      expect(genState.phase, GenerationPhase.idle);
      expect(genState.result, isNull);

      final configState = container.read(chartConfigNotifierProvider);
      expect(configState.dataKey, 'datasetB/file.parquet');
      expect(configState.sourceProductId, 'B');
      expect(configState.chartType, ChartType.line);
      expect(configState.title, '');
    });

    test('reset() clears customized config fields', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      final notifier = container.read(chartConfigNotifierProvider.notifier);
      notifier.setDataKey('old/key.parquet');
      notifier.setChartType(ChartType.scatter);
      notifier.setSizePreset(SizePreset.reddit);
      notifier.setCategory(BackgroundCategory.trade);
      notifier.setTitle('Old Headline');

      notifier.reset('new/key.parquet', sourceProductId: 'NEW');

      final state = container.read(chartConfigNotifierProvider);
      expect(state.dataKey, 'new/key.parquet');
      expect(state.sourceProductId, 'NEW');
      expect(state.chartType, ChartType.line);
      expect(state.sizePreset, SizePreset.instagram);
      expect(state.category, BackgroundCategory.housing);
      expect(state.title, '');
    });

    testWidgets('switching dataset clears title text field', (tester) async {
      String storageKey = 'key-A';
      late StateSetter outerSetState;

      const configA = ChartConfig(dataKey: 'key-A', title: '');

      await pumpLocalizedWidget(
        tester,
        StatefulBuilder(
          builder: (context, setState) {
            outerSetState = setState;
            return ChartConfigScreen(storageKey: storageKey);
          },
        ),
        overrides: [
          chartConfigNotifierProvider.overrideWith(
            () => _MockChartConfigNotifier(configA),
          ),
          chartGenerationNotifierProvider.overrideWith(
            () => _MockGenerationNotifier(const ChartGenerationState()),
          ),
        ],
      );
      await tester.pumpAndSettle();

      await tester.enterText(
        find.byKey(const Key('title_field')),
        'Housing Starts',
      );
      await tester.pumpAndSettle();
      expect(find.text('Housing Starts'), findsOneWidget);

      outerSetState(() => storageKey = 'key-B');
      await tester.pumpAndSettle();

      expect(find.text('Housing Starts'), findsNothing);
    });
  });

  group('ChartConfigNotifier unit tests', () {
    test('initial state has empty dataKey', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      final state = container.read(chartConfigNotifierProvider);
      expect(state.dataKey, '');
      expect(state.chartType, ChartType.line);
      expect(state.sizePreset, SizePreset.instagram);
      expect(state.category, BackgroundCategory.housing);
      expect(state.title, '');
    });

    test('setDataKey updates state', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      container
          .read(chartConfigNotifierProvider.notifier)
          .setDataKey('test/key.parquet', productId: '13-10-0888-01');
      final state = container.read(chartConfigNotifierProvider);
      expect(state.dataKey, 'test/key.parquet');
      expect(state.sourceProductId, '13-10-0888-01');
    });

    test('setChartType updates state', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      container
          .read(chartConfigNotifierProvider.notifier)
          .setChartType(ChartType.bar);
      final state = container.read(chartConfigNotifierProvider);
      expect(state.chartType, ChartType.bar);
    });

    test('setSizePreset updates state', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      container
          .read(chartConfigNotifierProvider.notifier)
          .setSizePreset(SizePreset.twitter);
      final state = container.read(chartConfigNotifierProvider);
      expect(state.sizePreset, SizePreset.twitter);
    });

    test('setCategory updates state', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      container
          .read(chartConfigNotifierProvider.notifier)
          .setCategory(BackgroundCategory.inflation);
      final state = container.read(chartConfigNotifierProvider);
      expect(state.category, BackgroundCategory.inflation);
    });

    test('setTitle updates state', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      container
          .read(chartConfigNotifierProvider.notifier)
          .setTitle('New Headline');
      final state = container.read(chartConfigNotifierProvider);
      expect(state.title, 'New Headline');
    });
  });
}
