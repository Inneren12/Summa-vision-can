import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:summa_vision_admin/core/theme/app_theme.dart';
import 'package:summa_vision_admin/features/kpi/application/kpi_providers.dart';
import 'package:summa_vision_admin/features/kpi/domain/kpi_data.dart';
import 'package:summa_vision_admin/features/kpi/presentation/kpi_screen.dart';

/// Sample KPI data used across tests.
KPIData _sampleKPI({
  int publishedCount = 42,
  int draftCount = 3,
  int totalLeads = 156,
  int b2bLeads = 38,
  int educationLeads = 12,
  int ispLeads = 8,
  int b2cLeads = 98,
  int emailsSent = 120,
  int tokensActivated = 89,
  int tokensExhausted = 12,
  int jobsSucceeded = 142,
  int jobsFailed = 8,
  int totalJobs = 156,
  Map<String, int>? failedByType,
  int dataContractViolations = 2,
  int catalogSyncs = 28,
}) {
  return KPIData(
    totalPublications: publishedCount + draftCount,
    publishedCount: publishedCount,
    draftCount: draftCount,
    totalLeads: totalLeads,
    b2bLeads: b2bLeads,
    educationLeads: educationLeads,
    ispLeads: ispLeads,
    b2cLeads: b2cLeads,
    espSyncedCount: 140,
    espFailedPermanentCount: 4,
    emailsSent: emailsSent,
    tokensCreated: 120,
    tokensActivated: tokensActivated,
    tokensExhausted: tokensExhausted,
    totalJobs: totalJobs,
    jobsSucceeded: jobsSucceeded,
    jobsFailed: jobsFailed,
    jobsQueued: 3,
    jobsRunning: 1,
    failedByType: failedByType ?? {'graphics_generate': 3, 'cube_fetch': 4, 'catalog_sync': 1},
    catalogSyncs: catalogSyncs,
    dataContractViolations: dataContractViolations,
    periodStart: DateTime.utc(2026, 3, 13),
    periodEnd: DateTime.utc(2026, 4, 12),
  );
}

/// Builds KPIScreen with mocked KPI data.
Widget _buildScreen(AsyncValue<KPIData> state, {int days = 30}) {
  return ProviderScope(
    overrides: [
      kpiDataProvider.overrideWith((ref) async {
        return switch (state) {
          AsyncData(:final value) => value,
          AsyncError(:final error) => throw error,
          _ => throw StateError('Use AsyncData or AsyncError'),
        };
      }),
      kpiPeriodDaysProvider.overrideWith((ref) => days),
    ],
    child: MaterialApp(
      theme: AppTheme.dark,
      home: const KPIScreen(),
    ),
  );
}

/// Scroll down until [finder] is visible in the first scrollable.
Future<void> _scrollUntilVisible(WidgetTester tester, Finder finder) async {
  await tester.scrollUntilVisible(
    finder,
    200.0,
    scrollable: find.byType(Scrollable).first,
  );
  await tester.pumpAndSettle();
}

void main() {
  group('KPIScreen — summary cards', () {
    testWidgets('renders 4 summary cards with correct numbers', (tester) async {
      await tester.pumpWidget(_buildScreen(AsyncData(_sampleKPI())));
      await tester.pumpAndSettle();

      // Publications card
      expect(find.text('42'), findsOneWidget);
      expect(find.text('Published'), findsOneWidget);
      expect(find.text('+3 drafts'), findsOneWidget);

      // Leads card
      expect(find.text('156'), findsOneWidget);
      expect(find.text('Leads'), findsOneWidget);
      expect(find.text('38 B2B'), findsOneWidget);

      // Downloads card
      expect(find.text('89'), findsOneWidget);
      expect(find.text('Downloads'), findsOneWidget);

      // Job Success card
      expect(find.text('Job Success'), findsOneWidget);
    });

    testWidgets('published count shows 42', (tester) async {
      await tester.pumpWidget(
        _buildScreen(AsyncData(_sampleKPI(publishedCount: 42))),
      );
      await tester.pumpAndSettle();

      expect(find.text('42'), findsOneWidget);
    });

    testWidgets('conversion rate shows ~74%', (tester) async {
      await tester.pumpWidget(
        _buildScreen(
          AsyncData(_sampleKPI(emailsSent: 120, tokensActivated: 89)),
        ),
      );
      await tester.pumpAndSettle();

      // 89/120 = 74.2%
      expect(find.textContaining('74.2%'), findsOneWidget);
    });

    testWidgets('job success rate shows ~94.7%', (tester) async {
      await tester.pumpWidget(
        _buildScreen(
          AsyncData(_sampleKPI(jobsSucceeded: 142, jobsFailed: 8)),
        ),
      );
      await tester.pumpAndSettle();

      // 142/(142+8) = 94.7%
      expect(find.textContaining('94.7%'), findsOneWidget);
    });

    testWidgets('division by zero shows N/A', (tester) async {
      await tester.pumpWidget(
        _buildScreen(
          AsyncData(_sampleKPI(emailsSent: 0, tokensActivated: 0)),
        ),
      );
      await tester.pumpAndSettle();

      // Downloads subtitle should be N/A
      expect(find.text('N/A'), findsWidgets);
    });
  });

  group('KPIScreen — funnel', () {
    testWidgets('funnel shows all 5 steps with counts', (tester) async {
      await tester.pumpWidget(_buildScreen(AsyncData(_sampleKPI())));
      await tester.pumpAndSettle();

      await _scrollUntilVisible(tester, find.text('Leads Captured'));
      expect(find.text('Leads Captured'), findsOneWidget);
      expect(find.text('Emails Sent'), findsOneWidget);
      expect(find.text('Tokens Created'), findsOneWidget);
      expect(find.text('Downloads'), findsWidgets); // also in summary card
      expect(find.text('Exhausted'), findsOneWidget);
    });
  });

  group('KPIScreen — lead breakdown', () {
    testWidgets('segments visible for B2B and Education', (tester) async {
      await tester.pumpWidget(
        _buildScreen(
          AsyncData(_sampleKPI(b2bLeads: 38, educationLeads: 12)),
        ),
      );
      await tester.pumpAndSettle();

      await _scrollUntilVisible(tester, find.text('B2B'));
      expect(find.text('B2B'), findsOneWidget);
      expect(find.text('Education'), findsOneWidget);
      expect(find.text('ISP'), findsOneWidget);
      expect(find.text('B2C'), findsOneWidget);
    });
  });

  group('KPIScreen — job failures', () {
    testWidgets('shows failure bar items', (tester) async {
      await tester.pumpWidget(
        _buildScreen(
          AsyncData(_sampleKPI(failedByType: {'graphics_generate': 3})),
        ),
      );
      await tester.pumpAndSettle();

      await _scrollUntilVisible(tester, find.text('Graphics Generate'));
      expect(find.text('Graphics Generate'), findsOneWidget);
      expect(find.text('3'), findsWidgets);
    });

    testWidgets('no failures shows good message', (tester) async {
      await tester.pumpWidget(
        _buildScreen(
          AsyncData(_sampleKPI(failedByType: {})),
        ),
      );
      await tester.pumpAndSettle();

      await _scrollUntilVisible(tester, find.text('No job failures in this period'));
      expect(find.text('No job failures in this period'), findsOneWidget);
    });
  });

  group('KPIScreen — data contract warning', () {
    testWidgets('shows warning when violations > 0', (tester) async {
      await tester.pumpWidget(
        _buildScreen(
          AsyncData(_sampleKPI(dataContractViolations: 5)),
        ),
      );
      await tester.pumpAndSettle();

      await _scrollUntilVisible(tester, find.byIcon(Icons.warning_amber_rounded));
      // Warning icon for violations
      expect(find.byIcon(Icons.warning_amber_rounded), findsOneWidget);
      expect(find.text('5'), findsWidgets);
    });
  });

  group('KPIScreen — period selector', () {
    testWidgets('changes period and reloads data', (tester) async {
      int? requestedDays;

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            kpiDataProvider.overrideWith((ref) async {
              requestedDays = ref.watch(kpiPeriodDaysProvider);
              return _sampleKPI();
            }),
          ],
          child: MaterialApp(
            theme: AppTheme.dark,
            home: const KPIScreen(),
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Initially 30 days
      expect(requestedDays, equals(30));

      // Tap "7 days" segment
      await tester.tap(find.text('7 days'));
      await tester.pumpAndSettle();

      expect(requestedDays, equals(7));
    });
  });

  group('KPIScreen — loading state', () {
    testWidgets('shows progress indicator while loading', (tester) async {
      final completer = Completer<KPIData>();

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            kpiDataProvider.overrideWith((ref) => completer.future),
          ],
          child: MaterialApp(theme: AppTheme.dark, home: const KPIScreen()),
        ),
      );
      await tester.pump();

      expect(find.byType(CircularProgressIndicator), findsOneWidget);
    });
  });

  group('KPIScreen — error state', () {
    testWidgets('shows error message and retry button', (tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            kpiDataProvider.overrideWith(
              (ref) => Future<KPIData>.error('Network error'),
            ),
          ],
          child: MaterialApp(theme: AppTheme.dark, home: const KPIScreen()),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.textContaining('Failed to load KPIs'), findsOneWidget);
      expect(find.text('Retry'), findsOneWidget);
    });
  });
}
