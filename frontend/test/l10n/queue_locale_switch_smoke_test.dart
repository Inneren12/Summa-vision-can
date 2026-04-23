import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:summa_vision_admin/core/app_bootstrap/app_bootstrap_provider.dart';
import 'package:summa_vision_admin/core/routing/app_router.dart';
import 'package:summa_vision_admin/features/queue/data/queue_repository.dart';
import 'package:summa_vision_admin/features/queue/domain/content_brief.dart';
import 'package:summa_vision_admin/features/queue/presentation/queue_screen.dart';
import 'package:summa_vision_admin/l10n/generated/app_localizations.dart';

const _brief = ContentBrief(
  id: 1,
  headline: 'Queue smoke headline',
  chartType: 'LINE',
  viralityScore: 8.7,
  status: 'DRAFT',
  createdAt: '2026-03-17T10:00:00Z',
);

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets('Queue strings rerender after EN -> RU switch', (tester) async {
    final router = GoRouter(
      initialLocation: AppRoutes.queue,
      routes: [
        GoRoute(
          path: AppRoutes.queue,
          builder: (_, __) => const QueueScreen(),
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

    expect(find.text('Brief Queue'), findsOneWidget);
    expect(find.text('Reject'), findsOneWidget);
    expect(find.text('Approve'), findsOneWidget);

    await tester.tap(find.byIcon(Icons.menu));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Russian'));
    await tester.pumpAndSettle();

    expect(find.text('Очередь брифов'), findsOneWidget);
    expect(find.text('Отклонить'), findsOneWidget);
    expect(find.text('Одобрить'), findsOneWidget);

    expect(find.text('Brief Queue'), findsNothing);
    expect(find.text('Reject'), findsNothing);
    expect(find.text('Approve'), findsNothing);
  });
}
