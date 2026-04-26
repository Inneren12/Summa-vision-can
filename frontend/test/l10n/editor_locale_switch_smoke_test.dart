import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:summa_vision_admin/core/shell/language_switcher.dart';
import 'package:summa_vision_admin/features/editor/presentation/editor_screen.dart';
import 'package:summa_vision_admin/features/queue/data/queue_repository.dart';
import 'package:summa_vision_admin/features/queue/domain/content_brief.dart';

import '../helpers/pump_localized_router.dart';

const _brief = ContentBrief(
  id: 42,
  headline: 'Smoke brief',
  chartType: 'LINE',
  viralityScore: 8.2,
  status: 'DRAFT',
  createdAt: '2026-04-24T00:00:00Z',
);

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets('Editor strings rerender after EN -> RU switch', (tester) async {
    final router = GoRouter(
      initialLocation: '/editor/42',
      routes: [
        GoRoute(
          path: '/editor/:briefId',
          builder: (context, state) => Scaffold(
            appBar: AppBar(actions: const [LanguageSwitcher()]),
            body: EditorScreen(briefId: state.pathParameters['briefId'] ?? '42'),
          ),
        ),
      ],
    );

    await pumpLocalizedRouter(
      tester,
      routerConfig: router,
      overrides: [
        queueProvider.overrideWith((ref) async => const [_brief]),
      ],
    );

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
    expect(find.text(enGenerate), findsNothing);
  });
}
