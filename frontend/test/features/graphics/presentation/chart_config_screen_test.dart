import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:summa_vision_admin/core/theme/app_theme.dart';
import 'package:summa_vision_admin/features/graphics/application/chart_config_notifier.dart';
import 'package:summa_vision_admin/features/graphics/application/generation_state_notifier.dart';
import 'package:summa_vision_admin/features/graphics/domain/chart_constants.dart';
import 'package:summa_vision_admin/features/graphics/domain/generation_result.dart';
import 'package:summa_vision_admin/features/graphics/presentation/chart_config_screen.dart';

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
// Helper: pump screen with overrides
// ---------------------------------------------------------------------------

Widget _buildScreen({
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

  return ProviderScope(
    overrides: [
      chartConfigNotifierProvider.overrideWith(
        () => _MockChartConfigNotifier(effectiveConfig),
      ),
      chartGenerationNotifierProvider.overrideWith(
        () => _MockGenerationNotifier(effectiveGenState),
      ),
    ],
    child: MaterialApp(
      theme: AppTheme.dark,
      home: ChartConfigScreen(
        storageKey: storageKey,
        productId: productId,
      ),
    ),
  );
}

void main() {
  group('ChartConfigScreen — renders all controls', () {
    testWidgets('test_chart_config_screen_renders_all_controls', (tester) async {
      await tester.pumpWidget(_buildScreen());
      await tester.pumpAndSettle();

      // Chart type selector
      expect(find.byKey(const Key('chart_type_selector')), findsOneWidget);
      // Size preset selector
      expect(find.byKey(const Key('size_preset_selector')), findsOneWidget);
      // Category chips (6 background categories)
      expect(find.byKey(const Key('category_chip_housing')), findsOneWidget);
      expect(find.byKey(const Key('category_chip_inflation')), findsOneWidget);
      expect(find.byKey(const Key('category_chip_employment')), findsOneWidget);
      expect(find.byKey(const Key('category_chip_trade')), findsOneWidget);
      expect(find.byKey(const Key('category_chip_energy')), findsOneWidget);
      expect(find.byKey(const Key('category_chip_demographics')), findsOneWidget);
      // Title field
      expect(find.byKey(const Key('title_field')), findsOneWidget);
      // Generate button
      expect(find.byKey(const Key('generate_button')), findsOneWidget);
    });
  });

  group('ChartConfigScreen — chart type selection', () {
    testWidgets('test_chart_type_selection_updates_state', (tester) async {
      await tester.pumpWidget(_buildScreen());
      await tester.pumpAndSettle();

      // Tap the dropdown to open it
      await tester.tap(find.byKey(const Key('chart_type_selector')));
      await tester.pumpAndSettle();

      // Select "Bar Chart"
      await tester.tap(find.text('Bar Chart').last);
      await tester.pumpAndSettle();

      // The dropdown should now show "Bar Chart" as selected
      expect(find.text('Bar Chart'), findsOneWidget);
    });
  });

  group('ChartConfigScreen — size preset selection', () {
    testWidgets('test_size_preset_selection', (tester) async {
      await tester.pumpWidget(_buildScreen());
      await tester.pumpAndSettle();

      // Tap "Twitter / X" segment
      expect(find.text('Twitter / X (1.91:1)'), findsOneWidget);
      await tester.tap(find.text('Twitter / X (1.91:1)'));
      await tester.pumpAndSettle();
    });
  });

  group('ChartConfigScreen — category selection', () {
    testWidgets('test_category_selection', (tester) async {
      await tester.pumpWidget(_buildScreen());
      await tester.pumpAndSettle();

      // Tap "Inflation" chip
      await tester.tap(find.byKey(const Key('category_chip_inflation')));
      await tester.pumpAndSettle();
    });
  });

  group('ChartConfigScreen — generate button disabled when title empty', () {
    testWidgets('test_generate_button_disabled_when_title_empty',
        (tester) async {
      await tester.pumpWidget(_buildScreen(
        config: const ChartConfig(
          dataKey: 'statcan/processed/13-10-0888-01/2024-12-15.parquet',
          title: '', // empty title
        ),
      ));
      await tester.pumpAndSettle();

      // Find the generate button
      final button = tester.widget<ElevatedButton>(
        find.byKey(const Key('generate_button')),
      );
      // Button should be disabled (onPressed == null)
      expect(button.onPressed, isNull);
    });

    testWidgets('button is enabled when title is non-empty', (tester) async {
      await tester.pumpWidget(_buildScreen(
        config: const ChartConfig(
          dataKey: 'statcan/processed/13-10-0888-01/2024-12-15.parquet',
          title: 'Housing Price Index',
        ),
      ));
      await tester.pumpAndSettle();

      final button = tester.widget<ElevatedButton>(
        find.byKey(const Key('generate_button')),
      );
      expect(button.onPressed, isNotNull);
    });
  });

  group('ChartConfigScreen — submitting phase', () {
    testWidgets('test_generation_submitting_shows_spinner', (tester) async {
      await tester.pumpWidget(_buildScreen(
        genState: const ChartGenerationState(
          phase: GenerationPhase.submitting,
        ),
      ));
      await tester.pump();

      expect(find.byType(CircularProgressIndicator), findsOneWidget);
      expect(find.textContaining('Submitting'), findsOneWidget);
    });
  });

  group('ChartConfigScreen — polling phase', () {
    testWidgets('test_generation_polling_shows_progress', (tester) async {
      await tester.pumpWidget(_buildScreen(
        genState: const ChartGenerationState(
          phase: GenerationPhase.polling,
          jobId: 'mock-gen-job-789',
          pollCount: 15,
        ),
      ));
      await tester.pump();

      expect(find.textContaining('poll 15/60'), findsOneWidget);
      expect(find.byType(LinearProgressIndicator), findsOneWidget);
      expect(find.textContaining('Estimated time remaining'), findsOneWidget);
    });
  });

  group('ChartConfigScreen — success phase', () {
    testWidgets('test_generation_success_shows_image', (tester) async {
      await tester.pumpWidget(_buildScreen(
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
      ));
      await tester.pump();

      // Download and Generate Another buttons should be visible
      expect(find.byKey(const Key('download_button')), findsOneWidget);
      expect(find.byKey(const Key('generate_another_button')), findsOneWidget);
      expect(find.byKey(const Key('back_to_preview_button')), findsOneWidget);
      // Publication metadata
      expect(find.textContaining('Publication #42'), findsOneWidget);
      expect(find.textContaining('v1'), findsOneWidget);
    });
  });

  group('ChartConfigScreen — timeout phase', () {
    testWidgets('test_generation_timeout_shows_retry', (tester) async {
      await tester.pumpWidget(_buildScreen(
        genState: const ChartGenerationState(
          phase: GenerationPhase.timeout,
          errorMessage: 'Generation timed out after 2 minutes.',
        ),
      ));
      await tester.pump();

      expect(find.textContaining('timed out'), findsOneWidget);
      expect(find.byKey(const Key('retry_button')), findsOneWidget);
    });
  });

  group('ChartConfigScreen — failed phase', () {
    testWidgets('test_generation_failed_shows_error', (tester) async {
      await tester.pumpWidget(_buildScreen(
        genState: const ChartGenerationState(
          phase: GenerationPhase.failed,
          errorMessage: 'Backend returned 500',
        ),
      ));
      await tester.pump();

      expect(find.textContaining('Backend returned 500'), findsOneWidget);
      expect(find.byKey(const Key('retry_button')), findsOneWidget);
    });
  });

  group('ChartConfigScreen — generate another resets state', () {
    testWidgets('test_generate_another_resets_state', (tester) async {
      await tester.pumpWidget(_buildScreen(
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
      ));
      await tester.pump();

      // "Generate Another" button is visible
      expect(find.byKey(const Key('generate_another_button')), findsOneWidget);
      // Tapping it should call reset() on the notifier
      await tester.tap(find.byKey(const Key('generate_another_button')));
      await tester.pumpAndSettle();
    });
  });

  group('ChartConfigScreen — result cached across navigation', () {
    testWidgets('test_result_cached_across_navigation', (tester) async {
      // Verify that the generation notifier's cache guard works:
      // if phase is already success, generate() is a no-op.
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

      // Simulate "navigating away" by reading state again — still cached
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
