import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:summa_vision_admin/features/graphics/application/chart_config_notifier.dart';
import 'package:summa_vision_admin/features/graphics/application/generation_state_notifier.dart';
import 'package:summa_vision_admin/features/graphics/domain/generation_result.dart';
import 'package:summa_vision_admin/features/graphics/presentation/chart_config_screen.dart';
import 'package:summa_vision_admin/l10n/generated/app_localizations.dart';

import '../../../helpers/localized_pump.dart';

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
    // no-op
  }

  /// Test hook for emitting subsequent states to simulate retry sequences
  /// without exercising the real notifier poll loop.
  void emit(ChartGenerationState next) => state = next;
}

Future<void> _pump(
  WidgetTester tester, {
  Locale locale = const Locale('en'),
  ChartConfig? config,
  ChartGenerationState? genState,
}) {
  final effectiveConfig = config ??
      const ChartConfig(
        dataKey: 'statcan/processed/13-10-0888-01/data.parquet',
        title: 'Test Headline',
      );
  final effectiveGenState = genState ?? const ChartGenerationState();
  return pumpLocalizedWidget(
    tester,
    const ChartConfigScreen(
      storageKey: 'statcan/processed/13-10-0888-01/data.parquet',
    ),
    locale: locale,
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
  group('ChartConfigScreen localization — EN', () {
    testWidgets('renders all localized chrome + labels', (tester) async {
      await _pump(tester);
      await tester.pumpAndSettle();

      final l10n = _l10n(tester);
      expect(find.text(l10n.chartConfigAppBarTitle), findsOneWidget);
      expect(find.text(l10n.chartConfigDataSourceStatcan), findsOneWidget);
      expect(find.text(l10n.chartConfigDataSourceUpload), findsOneWidget);
      expect(find.text(l10n.chartConfigDatasetLabel), findsOneWidget);
      expect(find.text(l10n.editorChartTypeLabel), findsOneWidget);
      expect(find.text(l10n.chartConfigSizePresetLabel), findsOneWidget);
      expect(find.text(l10n.chartConfigBackgroundCategoryLabel), findsOneWidget);
      expect(find.text(l10n.chartConfigHeadlineLabel), findsOneWidget);
      expect(find.text(l10n.editorGenerateGraphicButton), findsOneWidget);
    });

    testWidgets('polling view uses localized status + eta', (tester) async {
      await _pump(
        tester,
        genState: const ChartGenerationState(
          phase: GenerationPhase.polling,
          pollCount: 5,
        ),
      );
      await tester.pump();

      final l10n = _l10n(tester);
      expect(
        find.text(l10n.generationStatusPolling(5, ChartGenerationNotifier.maxPolls)),
        findsOneWidget,
      );
    });

    testWidgets('success view renders metadata chips + action buttons', (tester) async {
      await _pump(
        tester,
        genState: const ChartGenerationState(
          phase: GenerationPhase.success,
          result: GenerationResult(
            publicationId: 42,
            cdnUrlLowres: 'https://placehold.co/1080x1080.png',
            s3KeyHighres: 'publications/42/v1/hi.png',
            version: 3,
          ),
        ),
      );
      await tester.pump();

      final l10n = _l10n(tester);
      expect(find.text(l10n.chartConfigPublicationChip(42)), findsOneWidget);
      expect(find.text(l10n.chartConfigVersionChip('3')), findsOneWidget);
      expect(find.text(l10n.chartConfigDownloadPreviewButton), findsOneWidget);
      expect(find.text(l10n.chartConfigGenerateAnotherButton), findsOneWidget);
      expect(find.text(l10n.chartConfigBackToPreviewButton), findsOneWidget);
    });


    testWidgets(
      'UI does not show stale download after new failure',
      (tester) async {
        await _pump(
          tester,
          genState: const ChartGenerationState(
            phase: GenerationPhase.success,
            result: GenerationResult(
              publicationId: 7,
              cdnUrlLowres: 'https://placehold.co/1080x1080.png',
              s3KeyHighres: 'publications/7/v1/hi.png',
              version: 2,
            ),
          ),
        );
        await tester.pumpAndSettle();

        expect(find.byKey(const Key('download_button')), findsOneWidget);

        final container = ProviderScope.containerOf(
          tester.element(find.byType(ChartConfigScreen)),
        );
        final notifier =
            container.read(chartGenerationNotifierProvider.notifier)
                as _MockGenerationNotifier;
        notifier.emit(
          const ChartGenerationState(
            phase: GenerationPhase.failed,
            errorCode: 'CHART_EMPTY_DF',
            errorMessage: 'backend says empty',
          ),
        );
        await tester.pumpAndSettle();

        final l10n = _l10n(tester);
        expect(find.text(l10n.errorChartEmptyData), findsOneWidget);
        expect(find.byKey(const Key('download_button')), findsNothing);
        expect(find.byKey(const Key('generate_another_button')), findsNothing);
        expect(find.byKey(const Key('back_to_preview_button')), findsNothing);
      },
    );

    testWidgets('failed state falls back to localized status', (tester) async {
      await _pump(
        tester,
        genState: const ChartGenerationState(phase: GenerationPhase.failed),
      );
      await tester.pump();

      final l10n = _l10n(tester);
      expect(find.text(l10n.generationStatusFailed), findsOneWidget);
      expect(find.text(l10n.chartConfigTryAgainButton), findsOneWidget);
    });

    testWidgets(
      'failed state with known error_code renders localized mapped text (EN)',
      (tester) async {
        await _pump(
          tester,
          genState: const ChartGenerationState(
            phase: GenerationPhase.failed,
            errorCode: 'CHART_EMPTY_DF',
            errorMessage: 'raw backend text',
          ),
        );
        await tester.pump();

        final l10n = _l10n(tester);
        expect(find.text(l10n.errorChartEmptyData), findsOneWidget);
        expect(find.textContaining('raw backend text'), findsNothing);
      },
    );

    testWidgets(
      'clears stale localized message when subsequent failure has no code',
      (tester) async {
        // Step 1: coded failure → localized mapped text rendered.
        await _pump(
          tester,
          locale: const Locale('ru'),
          genState: const ChartGenerationState(
            phase: GenerationPhase.failed,
            errorCode: 'CHART_EMPTY_DF',
            errorMessage: 'data empty',
          ),
        );
        await tester.pump();
        final l10n = _l10n(tester);
        expect(find.text(l10n.errorChartEmptyData), findsOneWidget);

        // Step 2: retry emits a new failed state with NO code, only a raw
        // detail. The widget must swap to the raw passthrough and the
        // previous localized message must disappear.
        final container = ProviderScope.containerOf(
          tester.element(find.byType(ChartConfigScreen)),
        );
        final notifier = container
            .read(chartGenerationNotifierProvider.notifier)
            as _MockGenerationNotifier;
        notifier.emit(
          const ChartGenerationState(
            phase: GenerationPhase.failed,
            errorMessage: 'Different failure',
          ),
        );
        await tester.pump();

        expect(
          find.text(l10n.errorChartEmptyData),
          findsNothing,
          reason: 'stale localized text must be cleared',
        );
        expect(find.textContaining('Different failure'), findsOneWidget);
      },
    );

    testWidgets('timeout state uses unified timeout + commonRetryVerb', (tester) async {
      await _pump(
        tester,
        genState: const ChartGenerationState(phase: GenerationPhase.timeout),
      );
      await tester.pump();

      final l10n = _l10n(tester);
      expect(find.text(l10n.generationStatusTimeout), findsOneWidget);
      expect(find.text(l10n.commonRetryVerb), findsOneWidget);
    });
  });

  group('ChartConfigScreen localization — RU', () {
    testWidgets('renders localized RU chrome', (tester) async {
      await _pump(tester, locale: const Locale('ru'));
      await tester.pumpAndSettle();

      final l10n = _l10n(tester);
      expect(find.text(l10n.chartConfigAppBarTitle), findsOneWidget);
      expect(find.text(l10n.chartConfigDataSourceStatcan), findsOneWidget);
      expect(find.text(l10n.chartConfigSizePresetLabel), findsOneWidget);
    });

    testWidgets('BackgroundCategory chips render localized RU labels', (tester) async {
      await _pump(tester, locale: const Locale('ru'));
      await tester.pumpAndSettle();

      final l10n = _l10n(tester);
      expect(
        find.text(l10n.backgroundCategoryHousing, skipOffstage: false),
        findsAtLeastNWidgets(1),
      );
      expect(
        find.text(l10n.backgroundCategoryInflation, skipOffstage: false),
        findsAtLeastNWidgets(1),
      );
      expect(
        find.text(l10n.backgroundCategoryEmployment, skipOffstage: false),
        findsAtLeastNWidgets(1),
      );
      expect(
        find.text(l10n.backgroundCategoryTrade, skipOffstage: false),
        findsAtLeastNWidgets(1),
      );
      expect(
        find.text(l10n.backgroundCategoryEnergy, skipOffstage: false),
        findsAtLeastNWidgets(1),
      );
      expect(
        find.text(l10n.backgroundCategoryDemographics, skipOffstage: false),
        findsAtLeastNWidgets(1),
      );
    });

    testWidgets('ChartType dropdown values remain EN (Category D)', (tester) async {
      await _pump(tester, locale: const Locale('ru'));
      await tester.pumpAndSettle();

      expect(
        find.textContaining('Line Chart', skipOffstage: false),
        findsAtLeastNWidgets(1),
      );
    });

    testWidgets('SizePreset values remain EN (Category D)', (tester) async {
      await _pump(tester, locale: const Locale('ru'));
      await tester.pumpAndSettle();

      expect(
        find.textContaining('Instagram', skipOffstage: false),
        findsAtLeastNWidgets(1),
      );
      expect(
        find.textContaining('Twitter', skipOffstage: false),
        findsAtLeastNWidgets(1),
      );
      expect(
        find.textContaining('Reddit', skipOffstage: false),
        findsAtLeastNWidgets(1),
      );
    });

    testWidgets('size preset label uses amended RU form (Amendment 1)', (tester) async {
      await _pump(tester, locale: const Locale('ru'));
      await tester.pumpAndSettle();

      final l10n = _l10n(tester);
      expect(find.text(l10n.chartConfigSizePresetLabel), findsOneWidget);
    });

    testWidgets('headline max-char message uses amended RU form (Amendment 2)', (tester) async {
      await _pump(tester, locale: const Locale('ru'));
      await tester.pumpAndSettle();

      final l10n = _l10n(tester);
      expect(l10n.chartConfigHeadlineMaxChars, 'Не более 200 символов');
    });

    testWidgets(
      'failed state with known error_code renders localized mapped text (RU)',
      (tester) async {
        await _pump(
          tester,
          locale: const Locale('ru'),
          genState: const ChartGenerationState(
            phase: GenerationPhase.failed,
            errorCode: 'CHART_EMPTY_DF',
            errorMessage: 'raw backend text',
          ),
        );
        await tester.pump();

        final l10n = _l10n(tester);
        expect(find.text(l10n.errorChartEmptyData), findsOneWidget);
        expect(find.textContaining('raw backend text'), findsNothing);
      },
    );

    testWidgets('success state chips render with interpolated payload', (tester) async {
      await _pump(
        tester,
        locale: const Locale('ru'),
        genState: const ChartGenerationState(
          phase: GenerationPhase.success,
          result: GenerationResult(
            publicationId: 7,
            cdnUrlLowres: 'https://placehold.co/1080x1080.png',
            s3KeyHighres: 'publications/7/v1/hi.png',
            version: 2,
          ),
        ),
      );
      await tester.pump();

      expect(find.textContaining('Публикация №7'), findsOneWidget);
      expect(find.textContaining('v2'), findsOneWidget);
    });
  });
}
