import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:summa_vision_admin/features/queue/data/queue_repository.dart';
import 'package:summa_vision_admin/features/queue/domain/content_brief.dart';
import 'package:summa_vision_admin/features/queue/presentation/queue_screen.dart';
import '../../../helpers/localized_pump.dart';

/// Helper path/signature used by queue + router fixes:
/// `test/helpers/localized_pump.dart` ->
/// `pumpLocalizedWidget(tester, child, {locale, overrides})`.
Future<void> _pumpScreen(
  WidgetTester tester,
  AsyncValue<List<ContentBrief>> state,
) {
  return pumpLocalizedWidget(
    tester,
    const QueueScreen(),
    overrides: [
      queueProvider.overrideWith((ref) async {
        return switch (state) {
          AsyncData(:final value) => value,
          AsyncError(:final error) => throw error,
          _ => throw StateError('Use AsyncData or AsyncError'),
        };
      }),
    ],
  );
}

final _sampleBriefs = [
  const ContentBrief(
    id: 1,
    headline: 'Canadian housing prices surge 12%',
    chartType: 'BAR',
    viralityScore: 9.1,
    status: 'DRAFT',
    createdAt: '2026-03-17T10:00:00Z',
  ),
  const ContentBrief(
    id: 2,
    headline: 'CPI hits record high',
    chartType: 'LINE',
    viralityScore: 6.5,
    status: 'DRAFT',
    createdAt: '2026-03-17T09:00:00Z',
  ),
];

void main() {
  group('QueueScreen — loading state', () {
    testWidgets('shows CircularProgressIndicator while loading', (tester) async {
      final completer = Completer<List<ContentBrief>>();

      await pumpLocalizedWidget(
        tester,
        const QueueScreen(),
        overrides: [
          queueProvider.overrideWith(
            (ref) => completer.future,
          ),
        ],
      );
      await tester.pump();
      expect(find.byType(CircularProgressIndicator), findsOneWidget);
    });
  });

  group('QueueScreen — data state', () {
    testWidgets('renders brief cards for each item', (tester) async {
      await _pumpScreen(tester, AsyncData(_sampleBriefs));
      await tester.pumpAndSettle();

      expect(find.text('Canadian housing prices surge 12%'), findsOneWidget);
      expect(find.text('CPI hits record high'), findsOneWidget);
    });

    testWidgets('shows virality score for each brief', (tester) async {
      await _pumpScreen(tester, AsyncData(_sampleBriefs));
      await tester.pumpAndSettle();

      expect(find.text('9.1'), findsOneWidget);
      expect(find.text('6.5'), findsOneWidget);
    });

    testWidgets('shows chart type for each brief', (tester) async {
      await _pumpScreen(tester, AsyncData(_sampleBriefs));
      await tester.pumpAndSettle();

      expect(find.text('BAR'), findsOneWidget);
      expect(find.text('LINE'), findsOneWidget);
    });

    testWidgets('shows Approve and Reject buttons for each card', (tester) async {
      await _pumpScreen(tester, AsyncData([_sampleBriefs.first]));
      await tester.pumpAndSettle();

      expect(find.text('Approve'), findsOneWidget);
      expect(find.text('Reject'), findsOneWidget);
    });

    testWidgets('score >8 renders with data-positive colour', (tester) async {
      await _pumpScreen(tester, AsyncData([_sampleBriefs.first]));
      await tester.pumpAndSettle();

      // Score 9.1 > 8 should use dataPositive (design system token)
      final scoreText = tester.widget<Text>(find.text('9.1'));
      expect(scoreText.style?.color, equals(const Color(0xFF0D9488)));
    });
  });

  group('QueueScreen — empty state', () {
    testWidgets('shows empty message when list is empty', (tester) async {
      await _pumpScreen(tester, const AsyncData([]));
      await tester.pumpAndSettle();

      expect(find.textContaining('No briefs in queue'), findsOneWidget);
    });
  });

  group('QueueScreen — error state', () {
    testWidgets('shows error UI when fetch fails', (tester) async {
      await pumpLocalizedWidget(
        tester,
        const QueueScreen(),
        overrides: [
          queueProvider.overrideWith(
            (ref) => Future<List<ContentBrief>>.error('Network error'),
          ),
        ],
      );
      await tester.pumpAndSettle();

      expect(find.textContaining('Failed to load queue'), findsOneWidget);
      expect(find.text('Retry'), findsOneWidget);
    });
  });

  group('QueueScreen — refresh button', () {
    testWidgets('refresh icon button is present in AppBar', (tester) async {
      await _pumpScreen(tester, AsyncData(_sampleBriefs));
      await tester.pumpAndSettle();

      expect(find.byIcon(Icons.refresh), findsOneWidget);
    });

    testWidgets('tapping refresh invalidates queueProvider', (tester) async {
      var fetchCount = 0;

      await pumpLocalizedWidget(
        tester,
        const QueueScreen(),
        overrides: [
          queueProvider.overrideWith((ref) async {
            fetchCount++;
            return _sampleBriefs;
          }),
        ],
      );
      await tester.pumpAndSettle();

      final initialCount = fetchCount;
      await tester.tap(find.byIcon(Icons.refresh));
      await tester.pumpAndSettle();

      expect(fetchCount, greaterThan(initialCount));
    });
  });

  group('QueueScreen — Approve navigation', () {
    testWidgets('tapping Approve navigates to editor route', (tester) async {
      String? navigatedTo;

      final router = GoRouter(
        initialLocation: '/queue',
        routes: [
          GoRoute(
            path: '/queue',
            builder: (_, __) => ProviderScope(
              overrides: [
                queueProvider.overrideWith((ref) async => [_sampleBriefs.first]),
              ],
              child: const QueueScreen(),
            ),
          ),
          GoRoute(
            path: '/editor/:briefId',
            builder: (_, state) {
              navigatedTo = state.pathParameters['briefId'];
              return const Scaffold(body: Text('Editor'));
            },
          ),
        ],
      );

      await pumpLocalizedRouter(
        tester,
        router,
      );
      await tester.pumpAndSettle();

      await tester.tap(find.text('Approve'));
      await tester.pumpAndSettle();

      expect(navigatedTo, equals('1'));
    });
  });
}
