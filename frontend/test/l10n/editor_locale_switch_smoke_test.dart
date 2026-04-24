import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:summa_vision_admin/core/app_bootstrap/app_bootstrap_provider.dart';
import 'package:summa_vision_admin/core/shell/language_switcher.dart';
import 'package:summa_vision_admin/core/theme/app_theme.dart';
import 'package:summa_vision_admin/features/editor/presentation/editor_screen.dart';
import 'package:summa_vision_admin/features/queue/data/queue_repository.dart';
import 'package:summa_vision_admin/features/queue/domain/content_brief.dart';
import 'package:summa_vision_admin/l10n/generated/app_localizations.dart';

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

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          queueProvider.overrideWith((ref) async => const [_brief]),
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

    expect(find.text('Headline'), findsOneWidget);
    expect(find.text('Chart Type'), findsOneWidget);
    expect(find.text('Generate Graphic'), findsOneWidget);

    final russianButton = find.widgetWithText(
      TextButton,
      'Russian',
      skipOffstage: false,
    );
    expect(russianButton, findsOneWidget);
    await tester.tap(russianButton);
    await tester.pumpAndSettle();

    expect(find.text('Заголовок'), findsAtLeastNWidgets(1));
    expect(find.text('Тип графика'), findsAtLeastNWidgets(1));
    expect(find.text('Сгенерировать графику'), findsAtLeastNWidgets(1));
  });
}
