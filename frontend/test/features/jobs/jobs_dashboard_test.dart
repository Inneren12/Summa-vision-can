import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:summa_vision_admin/features/jobs/domain/job.dart';
import 'package:summa_vision_admin/features/jobs/domain/job_list_response.dart';
import 'package:summa_vision_admin/features/jobs/presentation/jobs_dashboard_screen.dart';
import 'package:mockito/mockito.dart';
import 'package:mockito/annotations.dart';
import 'package:summa_vision_admin/features/jobs/presentation/widgets/job_card.dart';
import 'package:summa_vision_admin/features/jobs/application/jobs_providers.dart';
import 'package:summa_vision_admin/features/jobs/data/job_dashboard_repository.dart';

import 'jobs_dashboard_test.mocks.dart';

@GenerateNiceMocks([MockSpec<JobDashboardRepository>()])
Widget createTestApp(ProviderContainer container) {
  return UncontrolledProviderScope(
    container: container,
    child: MaterialApp(
      home: Scaffold(
        body: const JobsDashboardScreen(),
      ),
    ),
  );
}

void main() {
  group('Jobs Dashboard Rendering Tests', () {
    testWidgets('test_jobs_dashboard_renders_job_cards', (tester) async {
      // Create only 2 jobs so they fit inside the default test viewport (800x600)
      final jobs = [
        Job(id: '1', jobType: 'catalog_sync', status: 'queued', attemptCount: 0, maxAttempts: 3, createdAt: DateTime.now()),
        Job(id: '2', jobType: 'cube_fetch', status: 'running', attemptCount: 1, maxAttempts: 3, createdAt: DateTime.now()),
      ];

      final container = ProviderContainer(
        overrides: [
          jobsListProvider.overrideWith((ref) => JobListResponse(items: jobs, total: 2)),
        ],
      );

      // Expand the viewport height just in case
      tester.view.physicalSize = const Size(800, 1200);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.reset());

      await tester.pumpWidget(createTestApp(container));
      await tester.pumpAndSettle();

      expect(find.byType(JobCard), findsNWidgets(2));
      expect(find.text('Catalog Sync'), findsOneWidget);
      expect(find.text('Data Fetch'), findsOneWidget);
      container.dispose();
    });

    testWidgets('test_jobs_dashboard_status_badge_colors', (tester) async {
      final jobs = [
        Job(id: '1', jobType: 'test', status: 'success', attemptCount: 1, maxAttempts: 3, createdAt: DateTime.now()),
        Job(id: '2', jobType: 'test', status: 'failed', attemptCount: 1, maxAttempts: 3, createdAt: DateTime.now()),
      ];

      final container = ProviderContainer(
        overrides: [
          jobsListProvider.overrideWith((ref) => JobListResponse(items: jobs, total: 2)),
        ],
      );

      await tester.pumpWidget(createTestApp(container));
      await tester.pumpAndSettle();

      // We can inspect the Container decorations to ensure colors are correct,
      // but simpler is to find the text and check the TextStyle color.
      final successTextFinder = find.descendant(
        of: find.byType(JobCard),
        matching: find.text('Success'),
      );
      expect(successTextFinder, findsOneWidget);
      final Text successText = tester.widget(successTextFinder);
      expect(successText.style?.color, Colors.green);

      final failedTextFinder = find.descendant(
        of: find.byType(JobCard),
        matching: find.text('Failed'),
      );
      expect(failedTextFinder, findsOneWidget);
      final Text failedText = tester.widget(failedTextFinder);
      expect(failedText.style?.color, Colors.red);
      container.dispose();
    });

    testWidgets('test_jobs_dashboard_stale_warning', (tester) async {
      final now = DateTime.now();
      final staleJob = Job(
        id: '1', jobType: 'test', status: 'running', attemptCount: 1, maxAttempts: 3,
        createdAt: now.subtract(const Duration(minutes: 20)),
        startedAt: now.subtract(const Duration(minutes: 15)),
      );

      final container = ProviderContainer(
        overrides: [
          jobsListProvider.overrideWith((ref) => JobListResponse(items: [staleJob], total: 1)),
        ],
      );

      await tester.pumpWidget(createTestApp(container));
      await tester.pumpAndSettle();

      expect(find.byIcon(Icons.warning), findsOneWidget);
      expect(find.textContaining('may be stale'), findsOneWidget);
      container.dispose();
    });

    testWidgets('test_jobs_dashboard_no_stale_warning_for_recent', (tester) async {
      final now = DateTime.now();
      final recentJob = Job(
        id: '1', jobType: 'test', status: 'running', attemptCount: 1, maxAttempts: 3,
        createdAt: now.subtract(const Duration(minutes: 5)),
        startedAt: now.subtract(const Duration(minutes: 2)),
      );

      final container = ProviderContainer(
        overrides: [
          jobsListProvider.overrideWith((ref) => JobListResponse(items: [recentJob], total: 1)),
        ],
      );

      await tester.pumpWidget(createTestApp(container));
      await tester.pumpAndSettle();

      expect(find.byIcon(Icons.warning), findsNothing);
      expect(find.textContaining('may be stale'), findsNothing);
      container.dispose();
    });
  });

  group('Jobs Dashboard Interaction Tests', () {
    testWidgets('test_retry_button_visible_for_retryable', (tester) async {
      final job = Job(id: '1', jobType: 'test', status: 'failed', attemptCount: 1, maxAttempts: 3, createdAt: DateTime.now());
      final container = ProviderContainer(
        overrides: [
          jobsListProvider.overrideWith((ref) => JobListResponse(items: [job], total: 1)),
        ],
      );

      await tester.pumpWidget(createTestApp(container));
      await tester.pumpAndSettle();

      expect(find.text('RETRY'), findsOneWidget);
      container.dispose();
    });

    testWidgets('test_retry_button_hidden_for_exhausted', (tester) async {
      final job = Job(id: '1', jobType: 'test', status: 'failed', attemptCount: 3, maxAttempts: 3, createdAt: DateTime.now());
      final container = ProviderContainer(
        overrides: [
          jobsListProvider.overrideWith((ref) => JobListResponse(items: [job], total: 1)),
        ],
      );

      await tester.pumpWidget(createTestApp(container));
      await tester.pumpAndSettle();

      expect(find.text('RETRY'), findsNothing);
      container.dispose();
    });

    testWidgets('test_retry_button_triggers_api', (tester) async {
      final job = Job(id: '1', jobType: 'test', status: 'failed', attemptCount: 1, maxAttempts: 3, createdAt: DateTime.now());
      final mockRepo = MockJobDashboardRepository();

      when(mockRepo.retryJob('1')).thenAnswer((_) async => 'new_job_id');

      final container = ProviderContainer(
        overrides: [
          jobsListProvider.overrideWith((ref) => JobListResponse(items: [job], total: 1)),
          jobDashboardRepositoryProvider.overrideWithValue(mockRepo),
        ],
      );

      await tester.pumpWidget(createTestApp(container));
      await tester.pumpAndSettle();

      await tester.tap(find.text('RETRY'));
      await tester.pumpAndSettle();

      verify(mockRepo.retryJob('1')).called(1);
      expect(find.textContaining('new_job_id'), findsOneWidget); // Snackbar text
      container.dispose();
    });

    testWidgets('test_job_detail_sheet_shows_payload', (tester) async {
      final job = Job(id: '1', jobType: 'test', status: 'success', payloadJson: '{"key":"value123"}', attemptCount: 1, maxAttempts: 3, createdAt: DateTime.now());
      final container = ProviderContainer(
        overrides: [
          jobsListProvider.overrideWith((ref) => JobListResponse(items: [job], total: 1)),
        ],
      );

      await tester.pumpWidget(createTestApp(container));
      await tester.pumpAndSettle();

      await tester.tap(find.text('VIEW DETAIL'));
      await tester.pumpAndSettle();

      expect(find.text('{"key":"value123"}'), findsOneWidget);
      container.dispose();
    });
  });

  group('Jobs Dashboard State & Filtering Tests', () {
    testWidgets('test_job_type_filter', (tester) async {
      final container = ProviderContainer(
        overrides: [
          jobsListProvider.overrideWith((ref) => const JobListResponse(items: [], total: 0)),
        ],
      );

      await tester.pumpWidget(createTestApp(container));
      await tester.pumpAndSettle();

      await tester.tap(find.text('All Types'));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Data Fetch').last);
      await tester.pumpAndSettle();

      final filter = container.read(jobFilterProvider);
      expect(filter.jobType, 'cube_fetch');
      container.dispose();
    });

    testWidgets('test_status_filter', (tester) async {
      final container = ProviderContainer(
        overrides: [
          jobsListProvider.overrideWith((ref) => const JobListResponse(items: [], total: 0)),
        ],
      );

      await tester.pumpWidget(createTestApp(container));
      await tester.pumpAndSettle();

      await tester.ensureVisible(find.text('Failed').last);
      await tester.tap(find.text('Failed').last);
      await tester.pumpAndSettle();

      final filter = container.read(jobFilterProvider);
      expect(filter.status, 'failed');
      container.dispose();
    });

    testWidgets('test_summary_stats_counts', (tester) async {
      final jobs = [
        Job(id: '1', jobType: 'test', status: 'queued', attemptCount: 0, maxAttempts: 3, createdAt: DateTime.now()),
        Job(id: '2', jobType: 'test', status: 'queued', attemptCount: 0, maxAttempts: 3, createdAt: DateTime.now()),
        Job(id: '3', jobType: 'test', status: 'running', attemptCount: 1, maxAttempts: 3, createdAt: DateTime.now()),
        Job(id: '4', jobType: 'test', status: 'success', attemptCount: 1, maxAttempts: 3, createdAt: DateTime.now()),
        Job(id: '5', jobType: 'test', status: 'success', attemptCount: 1, maxAttempts: 3, createdAt: DateTime.now()),
        Job(id: '6', jobType: 'test', status: 'success', attemptCount: 1, maxAttempts: 3, createdAt: DateTime.now()),
      ];
      final container = ProviderContainer(
        overrides: [
          jobsListProvider.overrideWith((ref) => JobListResponse(items: jobs, total: 6)),
        ],
      );

      await tester.pumpWidget(createTestApp(container));
      await tester.pumpAndSettle();

      expect(find.text('2'), findsNWidgets(1)); // 2 queued
      expect(find.text('1'), findsNWidgets(1)); // 1 running
      expect(find.text('3'), findsNWidgets(1)); // 3 success
      expect(find.text('0'), findsNWidgets(2)); // 0 failed, 0 stale
      container.dispose();
    });

    testWidgets('test_empty_state', (tester) async {
      final container = ProviderContainer(
        overrides: [
          jobsListProvider.overrideWith((ref) => const JobListResponse(items: [], total: 0)),
        ],
      );

      await tester.pumpWidget(createTestApp(container));
      await tester.pumpAndSettle();

      expect(find.textContaining('No jobs found'), findsOneWidget);
      container.dispose();
    });

    testWidgets('test_error_state', (tester) async {
      final container = ProviderContainer(
        overrides: [
          jobsListProvider.overrideWith((ref) => throw Exception('API Error')),
        ],
      );

      await tester.pumpWidget(createTestApp(container));
      await tester.pumpAndSettle();

      expect(find.textContaining('Error: Exception: API Error'), findsOneWidget);
      expect(find.text('Retry'), findsOneWidget);
      container.dispose();
    });

    testWidgets('test_auto_refresh', (tester) async {
      final container = ProviderContainer();

      await tester.pumpWidget(createTestApp(container));

      // Wait for a period that would trigger the timer (10s)
      await tester.pump(const Duration(seconds: 11));

      // Disposing will ensure the timer is cancelled and won't leak
      container.dispose();
    });
  });
}
