import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:summa_vision_admin/core/routing/app_router.dart';
import 'package:summa_vision_admin/features/queue/data/queue_repository.dart';
import 'package:summa_vision_admin/features/queue/domain/content_brief.dart';
import 'package:summa_vision_admin/features/queue/presentation/queue_screen.dart';

import '../helpers/pump_localized_router.dart';

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

    await pumpLocalizedRouter(
      tester,
      routerConfig: router,
      overrides: [
        queueProvider.overrideWith((ref) async => const [_brief]),
      ],
    );

    final enQueueTitle = l10n(tester).queueTitle;
    final enReject = l10n(tester).queueRejectVerb;
    final enApprove = l10n(tester).queueApproveVerb;

    expect(find.text(enQueueTitle), findsAtLeastNWidgets(1));
    expect(find.text(enReject), findsOneWidget);
    expect(find.text(enApprove), findsOneWidget);

    await tester.tap(find.byIcon(Icons.menu));
    await tester.pumpAndSettle();

    await switchLocaleVia(tester, 'ru');

    expect(find.text(l10n(tester).queueTitle), findsAtLeastNWidgets(1));
    expect(find.text(l10n(tester).queueRejectVerb), findsAtLeastNWidgets(1));
    expect(find.text(l10n(tester).queueApproveVerb), findsAtLeastNWidgets(1));

    expect(find.text(enQueueTitle), findsNothing);
    expect(find.text(enReject), findsNothing);
    expect(find.text(enApprove), findsNothing);
  });
}
