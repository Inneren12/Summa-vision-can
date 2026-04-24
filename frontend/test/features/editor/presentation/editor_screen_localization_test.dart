import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:summa_vision_admin/features/editor/presentation/editor_screen.dart';
import 'package:summa_vision_admin/features/queue/data/queue_repository.dart';
import 'package:summa_vision_admin/features/queue/domain/content_brief.dart';
import 'package:summa_vision_admin/l10n/generated/app_localizations.dart';
import '../../../helpers/localized_pump.dart';

const _brief = ContentBrief(
  id: 42,
  headline: 'Market momentum',
  chartType: 'BAR',
  viralityScore: 9.1,
  status: 'DRAFT',
  createdAt: '2026-04-24T00:00:00Z',
);

Future<void> _pump(
  WidgetTester tester, {
  Locale locale = const Locale('en'),
  Future<List<ContentBrief>> Function()? loader,
}) async {
  await pumpLocalizedWidget(
    tester,
    const EditorScreen(briefId: '42'),
    locale: locale,
    overrides: [
      queueProvider.overrideWith((ref) => loader?.call() ?? Future.value(const [_brief])),
    ],
  );
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('localized chrome renders for loaded brief in EN', (tester) async {
    await _pump(tester, locale: const Locale('en'));

    final context = tester.element(find.byType(EditorScreen));
    final l10n = AppLocalizations.of(context)!;

    expect(find.text(l10n.editorEditBriefTitle(42)), findsOneWidget);
    expect(find.text(l10n.editorHeadlineLabel), findsOneWidget);
    expect(find.text(l10n.editorBackgroundPromptLabel), findsOneWidget);
    expect(find.text(l10n.editorChartTypeLabel), findsOneWidget);
    expect(find.text(l10n.editorGenerateGraphicButton), findsOneWidget);
    expect(find.text(l10n.editorPreviewBackgroundButton), findsOneWidget);
    expect(find.text(l10n.editorViralityScoreLabel), findsOneWidget);

    await tester.enterText(find.byKey(const Key('headline_field')), 'Changed');
    await tester.pumpAndSettle();
    expect(find.text(l10n.editorResetVerb), findsOneWidget);
  });

  testWidgets('localized chrome renders for loaded brief in RU', (tester) async {
    await _pump(tester, locale: const Locale('ru'));

    final context = tester.element(find.byType(EditorScreen));
    final l10n = AppLocalizations.of(context)!;

    expect(find.text(l10n.editorEditBriefTitle(42)), findsOneWidget);
    expect(find.text(l10n.editorHeadlineLabel), findsOneWidget);
    expect(find.text(l10n.editorBackgroundPromptLabel), findsOneWidget);
    expect(find.text(l10n.editorChartTypeLabel), findsOneWidget);
    expect(find.text(l10n.editorGenerateGraphicButton), findsOneWidget);
    expect(find.text(l10n.editorPreviewBackgroundButton), findsOneWidget);
    expect(find.text(l10n.editorViralityScoreLabel), findsOneWidget);

    await tester.enterText(find.byKey(const Key('headline_field')), 'Изменено');
    await tester.pumpAndSettle();
    expect(find.text(l10n.editorResetVerb), findsOneWidget);
  });

  testWidgets('error state localizes wrapper in EN and RU', (tester) async {
    await _pump(
      tester,
      locale: const Locale('en'),
      loader: () => Future.error(Exception('Connection timeout')),
    );
    var context = tester.element(find.byType(EditorScreen));
    var l10n = AppLocalizations.of(context)!;

    expect(find.text(l10n.editorErrorAppBarTitle), findsOneWidget);
    expect(find.textContaining('Failed to load brief'), findsOneWidget);

    await _pump(
      tester,
      locale: const Locale('ru'),
      loader: () => Future.error(Exception('Connection timeout')),
    );
    context = tester.element(find.byType(EditorScreen));
    l10n = AppLocalizations.of(context)!;

    expect(find.text(l10n.editorErrorAppBarTitle), findsOneWidget);
    expect(find.textContaining('Не удалось загрузить'), findsOneWidget);
  });

  testWidgets('not-found state localizes appbar and body copy', (tester) async {
    await pumpLocalizedWidget(
      tester,
      const EditorScreen(briefId: '404'),
      locale: const Locale('ru'),
      overrides: [
        queueProvider.overrideWith((ref) async => const [_brief]),
      ],
    );
    await tester.pumpAndSettle();

    final context = tester.element(find.byType(EditorScreen));
    final l10n = AppLocalizations.of(context)!;

    expect(find.text(l10n.editorBriefNotFound), findsOneWidget);
    expect(find.text(l10n.editorNotFoundAppBarTitle), findsOneWidget);
  });

  testWidgets('chart type values remain EN in RU locale', (tester) async {
    await _pump(tester, locale: const Locale('ru'));

    await tester.tap(find.byKey(const Key('chart_type_dropdown')));
    await tester.pumpAndSettle();

    // skipOffstage: false — dropdown overlay renders 13 items which may clip
    // outside the 800×600 test viewport. Contract is existence in widget tree,
    // not visibility. Viewport clipping is a test-binding artifact.
    expect(find.text('Line', skipOffstage: false), findsWidgets);
    expect(find.text('Bar', skipOffstage: false), findsWidgets);
    expect(find.text('Choropleth (Canada)', skipOffstage: false), findsWidgets);
  });
}
