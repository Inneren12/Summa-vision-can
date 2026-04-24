import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:summa_vision_admin/core/routing/app_router.dart';
import 'package:summa_vision_admin/features/editor/presentation/editor_screen.dart';
import 'package:summa_vision_admin/features/queue/data/queue_repository.dart';
import 'package:summa_vision_admin/features/queue/domain/content_brief.dart';
import '../../helpers/localized_pump.dart';

const _brief = ContentBrief(
  id: 42,
  headline: 'Тестовый заголовок',
  chartType: 'BAR',
  viralityScore: 7.4,
  status: 'DRAFT',
  createdAt: '2026-04-24T00:00:00Z',
);

void main() {
  testWidgets('RU editor surface denies EN UI copy but allows EN chart labels', (
    tester,
  ) async {
    final router = GoRouter(
      initialLocation: '/editor/42',
      routes: [
        GoRoute(
          path: AppRoutes.editor,
          builder: (context, state) =>
              EditorScreen(briefId: state.pathParameters['briefId'] ?? '42'),
        ),
      ],
    );
    await pumpLocalizedRouter(
      tester,
      router,
      locale: const Locale('ru'),
      overrides: [queueProvider.overrideWith((ref) async => const [_brief])],
    );
    await tester.pumpAndSettle();

    const deniedExact = [
      'Editor',
      'Reset',
      'Virality Score',
      'Headline',
      'Enter headline...',
      'Background Prompt',
      'Chart Type',
      'Preview Background',
      'Generate Graphic',
      'Brief not found',
    ];

    for (final text in deniedExact) {
      expect(find.text(text, skipOffstage: false), findsNothing);
    }

    expect(find.textContaining('Edit Brief', skipOffstage: false), findsNothing);
    expect(find.textContaining('Describe the AI', skipOffstage: false), findsNothing);
    expect(
      find.textContaining('Failed to load brief', skipOffstage: false),
      findsNothing,
    );
    expect(
      find.textContaining('Editor action failed', skipOffstage: false),
      findsNothing,
    );

    // Allowlist per Category D (chart labels kept EN).
    await tester.tap(find.byKey(const Key('chart_type_dropdown')));
    await tester.pumpAndSettle();

    const chartAllowlist = [
      'Line',
      'Bar',
      'Scatter',
      'Area',
      'Stacked Bar',
      'Heatmap',
      'Candlestick',
      'Pie',
      'Donut',
      'Waterfall',
      'Treemap',
      'Bubble',
      'Choropleth (Canada)',
    ];

    for (final chartLabel in chartAllowlist) {
      expect(find.textContaining(chartLabel, skipOffstage: false), findsWidgets);
    }

    // Backend payload values are allowlisted.
    expect(find.textContaining('Тестовый заголовок'), findsOneWidget);
    expect(find.textContaining('7.4'), findsOneWidget);
    expect(find.textContaining('42'), findsWidgets);
  });
}
