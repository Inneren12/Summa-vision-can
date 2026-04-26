import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:summa_vision_admin/core/shell/language_switcher.dart';
import 'package:summa_vision_admin/features/editor/presentation/editor_screen.dart';
import 'package:summa_vision_admin/features/graphics/application/chart_config_notifier.dart';
import 'package:summa_vision_admin/features/graphics/application/generation_state_notifier.dart';
import 'package:summa_vision_admin/features/graphics/presentation/chart_config_screen.dart';
import 'package:summa_vision_admin/features/queue/data/queue_repository.dart';
import 'package:summa_vision_admin/features/queue/domain/content_brief.dart';
import 'package:summa_vision_admin/features/queue/presentation/queue_screen.dart';
import 'package:summa_vision_admin/l10n/generated/app_localizations_en.dart';

import '../helpers/pump_localized_router.dart';

const _brief = ContentBrief(
  id: 42,
  headline: 'Aggregator smoke headline',
  chartType: 'LINE',
  viralityScore: 8.4,
  status: 'DRAFT',
  createdAt: '2026-04-24T00:00:00Z',
);

const _chartStorageKey = 'statcan/processed/13-10-0888-01/data.parquet';

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

GoRouter _buildRouter({String initialLocation = '/queue'}) {
  return GoRouter(
    initialLocation: initialLocation,
    routes: [
      GoRoute(
        path: '/queue',
        builder: (context, state) => const QueueScreen(),
      ),
      GoRoute(
        path: '/editor/:briefId',
        builder: (context, state) => Scaffold(
          appBar: AppBar(actions: const [LanguageSwitcher()]),
          body: EditorScreen(
            briefId: state.pathParameters['briefId'] ?? '42',
          ),
        ),
      ),
      GoRoute(
        path: '/chart-config',
        builder: (context, state) => Scaffold(
          appBar: AppBar(actions: const [LanguageSwitcher()]),
          body: const ChartConfigScreen(storageKey: _chartStorageKey),
        ),
      ),
    ],
  );
}

GoRouter? _activeRouter;

Future<void> _pumpAppWithRouter(
  WidgetTester tester, {
  String initialLocation = '/queue',
}) async {
  final router = _buildRouter(initialLocation: initialLocation);
  _activeRouter = router;
  await pumpLocalizedRouter(
    tester,
    routerConfig: router,
    overrides: [
      queueProvider.overrideWith((ref) async => const [_brief]),
      chartConfigNotifierProvider.overrideWith(
        () => _MockChartConfigNotifier(
          const ChartConfig(
            dataKey: _chartStorageKey,
            title: 'Aggregator chart title',
          ),
        ),
      ),
      chartGenerationNotifierProvider.overrideWith(
        () => _MockGenerationNotifier(const ChartGenerationState()),
      ),
    ],
  );
}

void _navigate(String location) {
  _activeRouter!.go(location);
}

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
    _activeRouter = null;
  });

  group('App-wide locale switch — cross-feature traversal', () {
    testWidgets(
      'Queue → Editor: strings rerender after EN → RU switch',
      (tester) async {
        await _pumpAppWithRouter(tester);

        final enQueueTitle = l10n(tester).queueTitle;
        final enQueueApprove = l10n(tester).queueApproveVerb;

        expect(find.text(enQueueTitle), findsAtLeastNWidgets(1));
        expect(find.text(enQueueApprove), findsOneWidget);

        _navigate('/editor/42');
        await tester.pumpAndSettle();

        final enHeadline = l10n(tester).editorHeadlineLabel;
        final enChartType = l10n(tester).editorChartTypeLabel;
        final enGenerate = l10n(tester).editorGenerateGraphicButton;

        expect(find.text(enHeadline), findsOneWidget);
        expect(find.text(enChartType), findsOneWidget);
        expect(find.text(enGenerate), findsOneWidget);

        await switchLocaleVia(tester, 'ru');

        expect(find.text(l10n(tester).editorHeadlineLabel), findsAtLeastNWidgets(1));
        expect(find.text(l10n(tester).editorChartTypeLabel), findsAtLeastNWidgets(1));
        expect(
          find.text(l10n(tester).editorGenerateGraphicButton),
          findsAtLeastNWidgets(1),
        );

        expect(find.text(enHeadline), findsNothing);
        expect(find.text(enChartType), findsNothing);

        _navigate('/queue');
        await tester.pumpAndSettle();

        expect(find.text(l10n(tester).queueTitle), findsAtLeastNWidgets(1));
        expect(find.text(l10n(tester).queueApproveVerb), findsAtLeastNWidgets(1));
        expect(find.text(enQueueTitle), findsNothing);
        expect(find.text(enQueueApprove), findsNothing);
      },
    );

    testWidgets(
      'Queue → ChartConfig: strings rerender after EN → RU switch',
      (tester) async {
        await _pumpAppWithRouter(tester);

        final enQueueTitle = l10n(tester).queueTitle;
        expect(find.text(enQueueTitle), findsAtLeastNWidgets(1));

        _navigate('/chart-config');
        await tester.pumpAndSettle();

        final enChartConfig = l10n(tester).chartConfigAppBarTitle;
        final enDataset = l10n(tester).chartConfigDatasetLabel;
        final enBackground = l10n(tester).chartConfigBackgroundCategoryLabel;

        expect(find.text(enChartConfig), findsOneWidget);
        expect(find.text(enDataset), findsOneWidget);
        expect(find.text(enBackground), findsOneWidget);

        await switchLocaleVia(tester, 'ru');

        expect(find.text(l10n(tester).chartConfigAppBarTitle), findsAtLeastNWidgets(1));
        expect(find.text(l10n(tester).chartConfigDatasetLabel), findsAtLeastNWidgets(1));
        expect(
          find.text(l10n(tester).chartConfigBackgroundCategoryLabel),
          findsAtLeastNWidgets(1),
        );

        expect(find.text(enChartConfig), findsNothing);
        expect(find.text(enDataset), findsNothing);
        expect(find.text(enBackground), findsNothing);
      },
    );

    testWidgets(
      'Full journey: Queue → Editor → ChartConfig under RU',
      (tester) async {
        SharedPreferences.setMockInitialValues({'selected_locale': 'ru'});

        await _pumpAppWithRouter(tester);

        final en = AppLocalizationsEn();
        expect(find.text(l10n(tester).queueTitle), findsAtLeastNWidgets(1));
        expect(find.text(l10n(tester).queueApproveVerb), findsAtLeastNWidgets(1));
        expect(find.text(en.queueTitle), findsNothing);

        _navigate('/editor/42');
        await tester.pumpAndSettle();

        expect(find.text(l10n(tester).editorHeadlineLabel), findsAtLeastNWidgets(1));
        expect(find.text(l10n(tester).editorChartTypeLabel), findsAtLeastNWidgets(1));
        expect(
          find.text(l10n(tester).editorGenerateGraphicButton),
          findsAtLeastNWidgets(1),
        );
        expect(find.text(en.editorHeadlineLabel), findsNothing);
        expect(find.text(en.editorChartTypeLabel), findsNothing);

        _navigate('/chart-config');
        await tester.pumpAndSettle();

        expect(find.text(l10n(tester).chartConfigAppBarTitle), findsAtLeastNWidgets(1));
        expect(find.text(l10n(tester).chartConfigDatasetLabel), findsAtLeastNWidgets(1));
        expect(
          find.text(l10n(tester).chartConfigBackgroundCategoryLabel),
          findsAtLeastNWidgets(1),
        );
        expect(find.text(en.chartConfigAppBarTitle), findsNothing);
        expect(find.text(en.chartConfigDatasetLabel), findsNothing);
        expect(find.text(en.chartConfigBackgroundCategoryLabel), findsNothing);
      },
    );
  });
}
