import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:summa_vision_admin/core/app_bootstrap/app_bootstrap_provider.dart';
import 'package:summa_vision_admin/core/shell/language_switcher.dart';
import 'package:summa_vision_admin/core/theme/app_theme.dart';
import 'package:summa_vision_admin/features/editor/presentation/editor_screen.dart';
import 'package:summa_vision_admin/features/graphics/application/chart_config_notifier.dart';
import 'package:summa_vision_admin/features/graphics/application/generation_state_notifier.dart';
import 'package:summa_vision_admin/features/graphics/presentation/chart_config_screen.dart';
import 'package:summa_vision_admin/features/queue/data/queue_repository.dart';
import 'package:summa_vision_admin/features/queue/domain/content_brief.dart';
import 'package:summa_vision_admin/features/queue/presentation/queue_screen.dart';
import 'package:summa_vision_admin/l10n/generated/app_localizations.dart';

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

/// Builds a multi-route GoRouter covering /queue, /editor/:briefId, and
/// /chart-config. Each non-Queue route wraps its screen in a Scaffold whose
/// AppBar.actions hosts the LanguageSwitcher so tests can switch locale from
/// any screen without depending on the production drawer chrome.
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

/// Captured router for tests to drive navigation without traversing the
/// element tree (`GoRouter.of(context)` would fail at the MaterialApp level
/// since the router is established below).
GoRouter? _activeRouter;

Future<void> _pumpAppWithRouter(
  WidgetTester tester, {
  String initialLocation = '/queue',
}) async {
  final router = _buildRouter(initialLocation: initialLocation);
  _activeRouter = router;
  await tester.pumpWidget(
    ProviderScope(
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
      child: Consumer(
        builder: (context, ref, _) {
          final bootstrap = ref.watch(appBootstrapProvider);
          return MaterialApp.router(
            theme: AppTheme.dark,
            locale: bootstrap.when(
              data: (state) => state.locale,
              loading: () => const Locale('en'),
              error: (_, __) => const Locale('en'),
            ),
            supportedLocales: AppLocalizations.supportedLocales,
            localizationsDelegates: AppLocalizations.localizationsDelegates,
            routerConfig: router,
          );
        },
      ),
    ),
  );
  await tester.pumpAndSettle();
}

Future<void> _switchToRussianViaAppBar(WidgetTester tester) async {
  await tester.tap(
    find.widgetWithText(TextButton, 'Russian', skipOffstage: false),
  );
  await tester.pumpAndSettle();
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

        // Start at Queue (EN). queueTitle and navQueue share the same value;
        // findsAtLeastNWidgets(1) per Slice 3.3+3.4 lesson.
        expect(find.text('Brief Queue'), findsAtLeastNWidgets(1));
        expect(find.text('Approve'), findsOneWidget);

        // Navigate Queue → Editor.
        _navigate('/editor/42');
        await tester.pumpAndSettle();

        // Editor in EN.
        expect(find.text('Headline'), findsOneWidget);
        expect(find.text('Chart Type'), findsOneWidget);
        expect(find.text('Generate Graphic'), findsOneWidget);

        // Switch to RU via AppBar switcher (mounted by test wrapper).
        await _switchToRussianViaAppBar(tester);

        // Editor in RU.
        expect(find.text('Заголовок'), findsAtLeastNWidgets(1));
        expect(find.text('Тип графика'), findsAtLeastNWidgets(1));
        expect(find.text('Сгенерировать графику'), findsAtLeastNWidgets(1));

        // EN denial after switch.
        expect(find.text('Headline'), findsNothing);
        expect(find.text('Chart Type'), findsNothing);

        // Navigate back to Queue and confirm RU rendering there too.
        _navigate('/queue');
        await tester.pumpAndSettle();

        expect(find.text('Очередь брифов'), findsAtLeastNWidgets(1));
        expect(find.text('Одобрить'), findsAtLeastNWidgets(1));
        expect(find.text('Brief Queue'), findsNothing);
        expect(find.text('Approve'), findsNothing);
      },
    );

    testWidgets(
      'Queue → ChartConfig: strings rerender after EN → RU switch',
      (tester) async {
        await _pumpAppWithRouter(tester);

        // Queue in EN.
        expect(find.text('Brief Queue'), findsAtLeastNWidgets(1));

        // Navigate Queue → ChartConfig.
        _navigate('/chart-config');
        await tester.pumpAndSettle();

        // ChartConfig in EN.
        expect(find.text('Chart Configuration'), findsOneWidget);
        expect(find.text('Dataset'), findsOneWidget);
        expect(find.text('Background Category'), findsOneWidget);

        // Switch to RU via AppBar switcher.
        await _switchToRussianViaAppBar(tester);

        // ChartConfig in RU.
        expect(find.text('Настройка графика'), findsAtLeastNWidgets(1));
        expect(find.text('Набор данных'), findsAtLeastNWidgets(1));
        expect(find.text('Категория фона'), findsAtLeastNWidgets(1));

        // EN denial.
        expect(find.text('Chart Configuration'), findsNothing);
        expect(find.text('Dataset'), findsNothing);
        expect(find.text('Background Category'), findsNothing);
      },
    );

    testWidgets(
      'Full journey: Queue → Editor → ChartConfig under RU',
      (tester) async {
        // Start with persisted RU so all screens render in RU from first frame.
        SharedPreferences.setMockInitialValues({'selected_locale': 'ru'});

        await _pumpAppWithRouter(tester);

        // Queue in RU.
        expect(find.text('Очередь брифов'), findsAtLeastNWidgets(1));
        expect(find.text('Одобрить'), findsAtLeastNWidgets(1));
        expect(find.text('Brief Queue'), findsNothing);

        // Navigate to Editor.
        _navigate('/editor/42');
        await tester.pumpAndSettle();

        // Editor in RU.
        expect(find.text('Заголовок'), findsAtLeastNWidgets(1));
        expect(find.text('Тип графика'), findsAtLeastNWidgets(1));
        expect(find.text('Сгенерировать графику'), findsAtLeastNWidgets(1));
        expect(find.text('Headline'), findsNothing);
        expect(find.text('Chart Type'), findsNothing);

        // Navigate to ChartConfig.
        _navigate('/chart-config');
        await tester.pumpAndSettle();

        // ChartConfig in RU.
        expect(find.text('Настройка графика'), findsAtLeastNWidgets(1));
        expect(find.text('Набор данных'), findsAtLeastNWidgets(1));
        expect(find.text('Категория фона'), findsAtLeastNWidgets(1));
        expect(find.text('Chart Configuration'), findsNothing);
        expect(find.text('Dataset'), findsNothing);
        expect(find.text('Background Category'), findsNothing);
      },
    );
  });
}
