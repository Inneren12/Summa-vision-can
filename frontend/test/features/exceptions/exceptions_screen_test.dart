import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:summa_vision_admin/core/routing/app_router.dart';
import 'package:summa_vision_admin/core/theme/app_theme.dart';
import 'package:summa_vision_admin/features/exceptions/application/exceptions_providers.dart';
import 'package:summa_vision_admin/features/exceptions/domain/exception_filter.dart';
import 'package:summa_vision_admin/features/exceptions/presentation/exceptions_screen.dart';
import 'package:summa_vision_admin/features/jobs/data/job_dashboard_repository.dart';
import 'package:summa_vision_admin/features/jobs/domain/job.dart';
import 'package:summa_vision_admin/features/jobs/domain/job_list_response.dart';
import 'package:summa_vision_admin/l10n/generated/app_localizations.dart';

import '../../helpers/localized_pump.dart';

// ---------------------------------------------------------------------------
// Fixtures + fake repo
// ---------------------------------------------------------------------------

Job _job({
  required String id,
  String jobType = 'graphics_generate',
  String status = 'failed',
  DateTime? createdAt,
  DateTime? startedAt,
  String? errorCode,
}) {
  return Job(
    id: id,
    jobType: jobType,
    status: status,
    attemptCount: 1,
    maxAttempts: 3,
    createdAt: createdAt ?? DateTime.utc(2026, 4, 27, 10, 0, 0),
    startedAt: startedAt,
    errorCode: errorCode,
  );
}

class _FakeJobDashboardRepository extends JobDashboardRepository {
  _FakeJobDashboardRepository({JobListResponse? response})
      : _response = response ?? JobListResponse(items: [], total: 0),
        super(Dio());

  final JobListResponse _response;

  @override
  Future<JobListResponse> listJobs({
    String? jobType,
    String? status,
    int limit = 50,
  }) async {
    return _response;
  }
}

AppLocalizations _l10n(WidgetTester tester) {
  final scaffold = find.byType(Scaffold, skipOffstage: false);
  expect(scaffold, findsAtLeastNWidgets(1));
  return AppLocalizations.of(tester.element(scaffold.first))!;
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

void main() {
  group('ExceptionsScreen — chrome', () {
    testWidgets(
      'T-2.5-W-UNIT-01: AppBar title renders l10n.exceptionsTitle',
      (tester) async {
        await pumpLocalizedWidget(
          tester,
          const ExceptionsScreen(),
          overrides: [
            jobDashboardRepositoryProvider
                .overrideWith((ref) => _FakeJobDashboardRepository()),
          ],
        );
        await tester.pump();
        await tester.pump(const Duration(milliseconds: 50));

        final l10n = _l10n(tester);
        expect(
          find.widgetWithText(AppBar, l10n.exceptionsTitle),
          findsOneWidget,
        );
      },
    );

    testWidgets(
      'T-2.5-W-UNIT-02: refresh IconButton tap re-evaluates rows provider',
      (tester) async {
        var listJobsCallCount = 0;
        final fake = _CountingRepository(onCall: () => listJobsCallCount++);

        await pumpLocalizedWidget(
          tester,
          const ExceptionsScreen(),
          overrides: [
            jobDashboardRepositoryProvider.overrideWith((ref) => fake),
          ],
        );
        await tester.pump();
        await tester.pump(const Duration(milliseconds: 50));
        final initialCount = listJobsCallCount;

        await tester.tap(find.byIcon(Icons.refresh));
        await tester.pump();
        await tester.pump(const Duration(milliseconds: 50));

        expect(
          listJobsCallCount,
          greaterThan(initialCount),
          reason: 'refresh button should invalidate exceptionsRowsProvider, '
              'triggering a fresh listJobs() call',
        );
      },
    );
  });

  group('ExceptionsScreen — filter chips', () {
    testWidgets(
      'T-2.5-W-UNIT-03: three filter chips render with l10n labels and tapping '
      'a chip mutates exceptionsFilterProvider',
      (tester) async {
        // Hold a reference to the ProviderContainer so the test can read
        // the filter state after each tap.
        ProviderContainer? capturedContainer;

        await tester.pumpWidget(
          ProviderScope(
            overrides: [
              jobDashboardRepositoryProvider
                  .overrideWith((ref) => _FakeJobDashboardRepository()),
            ],
            child: Consumer(builder: (context, ref, _) {
              capturedContainer = ProviderScope.containerOf(context);
              return MaterialApp(
                theme: AppTheme.dark,
                supportedLocales: AppLocalizations.supportedLocales,
                localizationsDelegates:
                    AppLocalizations.localizationsDelegates,
                home: const ExceptionsScreen(),
              );
            }),
          ),
        );
        await tester.pump();
        await tester.pump(const Duration(milliseconds: 50));

        final l10n = _l10n(tester);
        final container = capturedContainer!;

        // All three chip labels are present.
        expect(
          find.widgetWithText(ChoiceChip, l10n.exceptionsFilterAll),
          findsAtLeastNWidgets(1),
        );
        expect(
          find.widgetWithText(
            ChoiceChip,
            l10n.exceptionsFilterFailedExports,
          ),
          findsAtLeastNWidgets(1),
        );
        expect(
          find.widgetWithText(ChoiceChip, l10n.exceptionsFilterZombieJobs),
          findsAtLeastNWidgets(1),
        );

        // Default filter is `all`.
        expect(
          container.read(exceptionsFilterProvider),
          ExceptionFilter.all,
        );

        // Tap "Failed Exports" → state becomes failedExports.
        await tester.tap(
          find.widgetWithText(
            ChoiceChip,
            l10n.exceptionsFilterFailedExports,
          ),
        );
        await tester.pump();
        await tester.pump(const Duration(milliseconds: 50));
        expect(
          container.read(exceptionsFilterProvider),
          ExceptionFilter.failedExports,
        );

        // Tap "Zombie Jobs" → state becomes zombieJobs.
        await tester.tap(
          find.widgetWithText(ChoiceChip, l10n.exceptionsFilterZombieJobs),
        );
        await tester.pump();
        await tester.pump(const Duration(milliseconds: 50));
        expect(
          container.read(exceptionsFilterProvider),
          ExceptionFilter.zombieJobs,
        );
      },
    );
  });

  group('ExceptionsScreen — async states', () {
    testWidgets(
      'T-2.5-W-UNIT-04: empty state renders l10n.exceptionsEmptyState when '
      'rows resolves to []',
      (tester) async {
        await pumpLocalizedWidget(
          tester,
          const ExceptionsScreen(),
          overrides: [
            jobDashboardRepositoryProvider
                .overrideWith((ref) => _FakeJobDashboardRepository()),
          ],
        );
        await tester.pump();
        await tester.pump(const Duration(milliseconds: 50));

        final l10n = _l10n(tester);
        expect(find.text(l10n.exceptionsEmptyState), findsOneWidget);
      },
    );

    testWidgets(
      'T-2.5-W-UNIT-05: error state renders l10n.exceptionsLoadError and the '
      'retry button re-fetches',
      (tester) async {
        var attempt = 0;

        await pumpLocalizedWidget(
          tester,
          const ExceptionsScreen(),
          overrides: [
            jobDashboardRepositoryProvider.overrideWith(
              (ref) => _ThrowingRepository(onCall: () => attempt++),
            ),
          ],
        );
        await tester.pump();
        await tester.pump(const Duration(milliseconds: 50));

        final l10n = _l10n(tester);
        expect(
          find.textContaining(
            l10n.exceptionsLoadError('').replaceAll('\n', '').trim(),
          ),
          findsAtLeastNWidgets(1),
          reason: 'error state should render the load-error template',
        );
        expect(find.text(l10n.commonRetryVerb), findsOneWidget);

        final initialAttempts = attempt;
        await tester.tap(find.text(l10n.commonRetryVerb));
        await tester.pump();
        await tester.pump(const Duration(milliseconds: 50));
        expect(
          attempt,
          greaterThan(initialAttempts),
          reason: 'retry button must invalidate the rows provider',
        );
      },
    );

    testWidgets(
      'T-2.5-W-UNIT-06: 3 jobs render exactly 3 JobCards in ListView.separated',
      (tester) async {
        final jobs = [
          _job(id: 'fe-1', errorCode: 'STORAGE_ERROR'),
          _job(id: 'fe-2', errorCode: 'CHART_EMPTY_DF'),
          _job(id: 'fe-3', errorCode: 'CHART_INSUFFICIENT_COLUMNS'),
        ];
        await pumpLocalizedWidget(
          tester,
          const ExceptionsScreen(),
          overrides: [
            jobDashboardRepositoryProvider.overrideWith(
              (ref) => _FakeJobDashboardRepository(
                response: JobListResponse(items: jobs, total: jobs.length),
              ),
            ),
          ],
        );
        await tester.pump();
        await tester.pump(const Duration(milliseconds: 50));

        // JobCard wraps content in a Material Card, and each card has a
        // jobTypeDisplay text — "Chart Generation" for graphics_generate.
        // Anchoring on jobTypeDisplay is more stable than counting cards by
        // type lookup because Card is also used elsewhere in the tree.
        // skipOffstage: false because ListView.separated is lazy and the
        // 800x600 default viewport clips the 3rd card off-stage; the
        // off-stage card is built but not visible.
        expect(
          find.text('Chart Generation', skipOffstage: false),
          findsNWidgets(3),
        );
        expect(find.byType(ListView), findsOneWidget);
      },
    );
  });

  group('ExceptionsScreen — drawer navigation', () {
    testWidgets(
      'T-2.5-W-INT-01: tapping the Exceptions drawer entry navigates to /exceptions',
      (tester) async {
        await tester.binding.setSurfaceSize(const Size(1200, 900));
        addTearDown(() => tester.binding.setSurfaceSize(null));

        await tester.pumpWidget(
          ProviderScope(
            overrides: [
              jobDashboardRepositoryProvider
                  .overrideWith((ref) => _FakeJobDashboardRepository()),
            ],
            child: Consumer(builder: (context, ref, _) {
              final router = ref.watch(routerProvider);
              return MaterialApp.router(
                theme: AppTheme.dark,
                supportedLocales: AppLocalizations.supportedLocales,
                localizationsDelegates:
                    AppLocalizations.localizationsDelegates,
                routerConfig: router,
              );
            }),
          ),
        );
        await tester.pump();
        await tester.pump(const Duration(milliseconds: 50));

        // App starts at /queue (initialLocation in app_router.dart).
        // Open the drawer.
        final scaffoldState =
            tester.firstState<ScaffoldState>(find.byType(Scaffold));
        scaffoldState.openDrawer();
        await tester.pump();
        await tester.pump(const Duration(milliseconds: 200));

        final l10n = _l10n(tester);
        // Tap the Exceptions entry inside the drawer.
        await tester.tap(find.text(l10n.navExceptions));
        await tester.pump();
        await tester.pump(const Duration(milliseconds: 200));

        // ExceptionsScreen now renders — assert via its AppBar title which
        // reads l10n.exceptionsTitle, distinct from any other screen's title.
        expect(
          find.widgetWithText(AppBar, l10n.exceptionsTitle),
          findsOneWidget,
        );
      },
    );
  });
}

// ---------------------------------------------------------------------------
// Test helpers (additional fakes scoped to widget tests)
// ---------------------------------------------------------------------------

class _CountingRepository extends JobDashboardRepository {
  _CountingRepository({required this.onCall}) : super(Dio());
  final void Function() onCall;

  @override
  Future<JobListResponse> listJobs({
    String? jobType,
    String? status,
    int limit = 50,
  }) async {
    onCall();
    return JobListResponse(items: [], total: 0);
  }
}

class _ThrowingRepository extends JobDashboardRepository {
  _ThrowingRepository({required this.onCall}) : super(Dio());
  final void Function() onCall;

  @override
  Future<JobListResponse> listJobs({
    String? jobType,
    String? status,
    int limit = 50,
  }) async {
    onCall();
    throw const _FakeNetworkError();
  }
}

class _FakeNetworkError implements Exception {
  const _FakeNetworkError();
  @override
  String toString() => 'FakeNetworkError';
}
