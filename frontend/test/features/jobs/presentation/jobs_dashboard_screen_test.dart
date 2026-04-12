import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:summa_vision_admin/core/theme/app_theme.dart';
import 'package:summa_vision_admin/features/jobs/application/jobs_providers.dart';
import 'package:summa_vision_admin/features/jobs/data/job_dashboard_repository.dart';
import 'package:summa_vision_admin/features/jobs/domain/job.dart';
import 'package:summa_vision_admin/features/jobs/domain/job_filter.dart';
import 'package:summa_vision_admin/features/jobs/domain/job_list_response.dart';
import 'package:summa_vision_admin/features/jobs/presentation/jobs_dashboard_screen.dart';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

Job _makeJob({
  String id = 'job-001',
  String jobType = 'graphics_generate',
  String status = 'success',
  int attemptCount = 1,
  int maxAttempts = 3,
  DateTime? createdAt,
  DateTime? startedAt,
  DateTime? finishedAt,
  String? errorCode,
  String? errorMessage,
  String? dedupeKey,
  String? createdBy = 'admin_api',
}) {
  return Job(
    id: id,
    jobType: jobType,
    status: status,
    attemptCount: attemptCount,
    maxAttempts: maxAttempts,
    createdAt: createdAt ?? DateTime.now(),
    startedAt: startedAt,
    finishedAt: finishedAt,
    errorCode: errorCode,
    errorMessage: errorMessage,
    dedupeKey: dedupeKey,
    createdBy: createdBy,
  );
}

Widget _buildScreen(
  AsyncValue<JobListResponse> state, {
  List<Override> extraOverrides = const [],
}) {
  return ProviderScope(
    overrides: [
      jobsListProvider.overrideWith((ref) async {
        return switch (state) {
          AsyncData(:final value) => value,
          AsyncError(:final error) => throw error,
          _ => throw StateError('Use AsyncData or AsyncError'),
        };
      }),
      // Disable auto-refresh in tests
      autoRefreshProvider.overrideWith((ref) {}),
      ...extraOverrides,
    ],
    child: MaterialApp(
      theme: AppTheme.dark,
      home: const JobsDashboardScreen(),
    ),
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

void main() {
  group('JobsDashboardScreen — renders job cards', () {
    testWidgets('renders correct number of job cards', (tester) async {
      final jobs = [
        _makeJob(id: 'j1', status: 'queued'),
        _makeJob(id: 'j2', status: 'running', startedAt: DateTime.now()),
        _makeJob(id: 'j3', status: 'success'),
      ];
      final response = JobListResponse(items: jobs, total: 3);

      await tester.pumpWidget(_buildScreen(AsyncData(response)));
      await tester.pumpAndSettle();

      // Should find 3 Card widgets for the jobs
      expect(find.text('Chart Generation'), findsNWidgets(3));
    });
  });

  group('JobsDashboardScreen — status badge colors', () {
    testWidgets('shows correct status text for different statuses',
        (tester) async {
      final jobs = [
        _makeJob(id: 'j1', status: 'success'),
        _makeJob(id: 'j2', status: 'failed', errorCode: 'ERR'),
        _makeJob(id: 'j3', status: 'queued'),
      ];
      final response = JobListResponse(items: jobs, total: 3);

      await tester.pumpWidget(_buildScreen(AsyncData(response)));
      await tester.pumpAndSettle();

      expect(find.text('Success'), findsOneWidget);
      expect(find.text('Failed'), findsWidgets); // also in filter chip
      expect(find.text('Queued'), findsWidgets); // also in filter chip
    });
  });

  group('JobsDashboardScreen — stale warning', () {
    testWidgets('shows stale warning for job running > 10 min',
        (tester) async {
      final staleJob = _makeJob(
        id: 'j-stale',
        status: 'running',
        startedAt: DateTime.now().subtract(const Duration(minutes: 15)),
      );
      final response = JobListResponse(items: [staleJob], total: 1);

      await tester.pumpWidget(_buildScreen(AsyncData(response)));
      await tester.pumpAndSettle();

      expect(find.byIcon(Icons.warning_amber), findsOneWidget);
      expect(find.textContaining('may be stale'), findsOneWidget);
    });

    testWidgets('no stale warning for recent running job', (tester) async {
      final recentJob = _makeJob(
        id: 'j-recent',
        status: 'running',
        startedAt: DateTime.now().subtract(const Duration(minutes: 2)),
      );
      final response = JobListResponse(items: [recentJob], total: 1);

      await tester.pumpWidget(_buildScreen(AsyncData(response)));
      await tester.pumpAndSettle();

      expect(find.textContaining('may be stale'), findsNothing);
    });
  });

  group('JobsDashboardScreen — retry button', () {
    testWidgets('visible for retryable failed job', (tester) async {
      final retryableJob = _makeJob(
        id: 'j-fail',
        status: 'failed',
        attemptCount: 1,
        maxAttempts: 3,
        errorCode: 'STORAGE_ERROR',
      );
      final response = JobListResponse(items: [retryableJob], total: 1);

      await tester.pumpWidget(_buildScreen(AsyncData(response)));
      await tester.pumpAndSettle();

      expect(find.text('Retry'), findsOneWidget);
    });

    testWidgets('hidden for exhausted failed job', (tester) async {
      final exhaustedJob = _makeJob(
        id: 'j-exhausted',
        status: 'failed',
        attemptCount: 3,
        maxAttempts: 3,
        errorCode: 'DATA_CONTRACT_VIOLATION',
      );
      final response = JobListResponse(items: [exhaustedJob], total: 1);

      await tester.pumpWidget(_buildScreen(AsyncData(response)));
      await tester.pumpAndSettle();

      // "Retry" button text should NOT be present (but "Retry" in the
      // error state button is different — check for OutlinedButton specifically)
      expect(
        find.widgetWithText(OutlinedButton, 'Retry'),
        findsNothing,
      );
    });
  });

  group('JobsDashboardScreen — job detail sheet', () {
    testWidgets('tapping View Detail opens bottom sheet with payload',
        (tester) async {
      final job = _makeJob(
        id: 'j-detail',
        status: 'success',
        startedAt: DateTime.utc(2026, 4, 10, 14, 30, 0),
        finishedAt: DateTime.utc(2026, 4, 10, 14, 30, 24),
      );
      job.copyWith(payloadJson: '{"key":"value"}');
      // Use a job with payloadJson
      final jobWithPayload = Job(
        id: 'j-detail',
        jobType: 'graphics_generate',
        status: 'success',
        attemptCount: 1,
        maxAttempts: 3,
        createdAt: DateTime.utc(2026, 4, 10, 14, 30, 0),
        startedAt: DateTime.utc(2026, 4, 10, 14, 30, 0),
        finishedAt: DateTime.utc(2026, 4, 10, 14, 30, 24),
        payloadJson: '{"key":"value"}',
        createdBy: 'admin_api',
      );
      final response = JobListResponse(items: [jobWithPayload], total: 1);

      await tester.pumpWidget(_buildScreen(AsyncData(response)));
      await tester.pumpAndSettle();

      await tester.tap(find.text('View Detail'));
      await tester.pumpAndSettle();

      // Bottom sheet should show "Job Detail" heading
      expect(find.text('Job Detail'), findsOneWidget);
      // And the payload section
      expect(find.text('Payload'), findsOneWidget);
    });
  });

  group('JobsDashboardScreen — summary stats', () {
    testWidgets('shows correct status counts', (tester) async {
      final jobs = [
        _makeJob(id: 'j1', status: 'queued'),
        _makeJob(id: 'j2', status: 'queued'),
        _makeJob(
          id: 'j3',
          status: 'running',
          startedAt: DateTime.now().subtract(const Duration(minutes: 2)),
        ),
        _makeJob(id: 'j4', status: 'success'),
        _makeJob(id: 'j5', status: 'success'),
        _makeJob(id: 'j6', status: 'success'),
      ];
      final response = JobListResponse(items: jobs, total: 6);

      await tester.pumpWidget(_buildScreen(AsyncData(response)));
      await tester.pumpAndSettle();

      // Stats bar should show counts
      // "Queued: 2"
      expect(find.text('2'), findsWidgets); // queued count
      // "Running: 1"
      expect(find.text('1'), findsWidgets); // running count
      // "Success: 3"
      expect(find.text('3'), findsWidgets); // success count
    });
  });

  group('JobsDashboardScreen — auto-refresh', () {
    testWidgets('auto-refresh provider is watched', (tester) async {
      bool autoRefreshWatched = false;

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            jobsListProvider.overrideWith((ref) async {
              return JobListResponse(items: [], total: 0);
            }),
            autoRefreshProvider.overrideWith((ref) {
              autoRefreshWatched = true;
            }),
          ],
          child: MaterialApp(
            theme: AppTheme.dark,
            home: const JobsDashboardScreen(),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(autoRefreshWatched, isTrue);
    });
  });

  group('JobsDashboardScreen — empty state', () {
    testWidgets('shows empty message when no jobs', (tester) async {
      final response = JobListResponse(items: [], total: 0);

      await tester.pumpWidget(_buildScreen(AsyncData(response)));
      await tester.pumpAndSettle();

      expect(find.text('No jobs found. Adjust filters or wait for new jobs.'),
          findsOneWidget);
    });
  });

  group('JobsDashboardScreen — error state', () {
    testWidgets('shows error message and retry button', (tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            jobsListProvider.overrideWith(
              (ref) => Future<JobListResponse>.error('Network error'),
            ),
            autoRefreshProvider.overrideWith((ref) {}),
          ],
          child: MaterialApp(
            theme: AppTheme.dark,
            home: const JobsDashboardScreen(),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.textContaining('Failed to load jobs'), findsOneWidget);
      expect(find.text('Retry'), findsOneWidget);
    });
  });

  group('JobsDashboardScreen — filters', () {
    testWidgets('status filter chips are displayed', (tester) async {
      final response = JobListResponse(items: [], total: 0);

      await tester.pumpWidget(_buildScreen(AsyncData(response)));
      await tester.pumpAndSettle();

      expect(find.text('All'), findsOneWidget);
      expect(find.text('Queued'), findsOneWidget);
      expect(find.text('Running'), findsOneWidget);
      expect(find.text('Success'), findsOneWidget);
      expect(find.text('Failed'), findsOneWidget);
    });
  });

  group('JobsDashboardScreen — loading state', () {
    testWidgets('shows progress indicator while loading', (tester) async {
      final completer = Completer<JobListResponse>();

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            jobsListProvider.overrideWith((ref) => completer.future),
            autoRefreshProvider.overrideWith((ref) {}),
          ],
          child: MaterialApp(
            theme: AppTheme.dark,
            home: const JobsDashboardScreen(),
          ),
        ),
      );
      await tester.pump();

      expect(find.byType(CircularProgressIndicator), findsOneWidget);
    });
  });
}
