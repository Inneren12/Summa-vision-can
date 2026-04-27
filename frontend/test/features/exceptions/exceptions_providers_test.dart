import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:summa_vision_admin/features/exceptions/application/exceptions_providers.dart';
import 'package:summa_vision_admin/features/exceptions/domain/exception_filter.dart';
import 'package:summa_vision_admin/features/jobs/data/job_dashboard_repository.dart';
import 'package:summa_vision_admin/features/jobs/domain/job.dart';
import 'package:summa_vision_admin/features/jobs/domain/job_list_response.dart';

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

Job _job({
  required String id,
  String jobType = 'graphics_generate',
  String status = 'failed',
  DateTime? createdAt,
  DateTime? startedAt,
}) {
  return Job(
    id: id,
    jobType: jobType,
    status: status,
    attemptCount: 1,
    maxAttempts: 3,
    createdAt: createdAt ?? DateTime.utc(2026, 4, 27, 10, 0, 0),
    startedAt: startedAt,
  );
}

class _ListJobsCall {
  _ListJobsCall({this.jobType, this.status, required this.limit});
  final String? jobType;
  final String? status;
  final int limit;
}

/// Fake [JobDashboardRepository] that records each [listJobs] invocation
/// and returns a scripted response based on `(jobType, status)`.
class _FakeJobDashboardRepository extends JobDashboardRepository {
  _FakeJobDashboardRepository({
    JobListResponse? failedExports,
    JobListResponse? running,
  })  : _failedExports = failedExports ?? JobListResponse(items: [], total: 0),
        _running = running ?? JobListResponse(items: [], total: 0),
        super(Dio());

  final JobListResponse _failedExports;
  final JobListResponse _running;
  final List<_ListJobsCall> calls = [];

  @override
  Future<JobListResponse> listJobs({
    String? jobType,
    String? status,
    int limit = 50,
  }) async {
    calls.add(_ListJobsCall(jobType: jobType, status: status, limit: limit));
    if (jobType == 'graphics_generate' && status == 'failed') {
      return _failedExports;
    }
    if (status == 'running') {
      return _running;
    }
    return JobListResponse(items: [], total: 0);
  }
}

ProviderContainer _container(
  _FakeJobDashboardRepository fake, {
  ExceptionFilter? initialFilter,
}) {
  final container = ProviderContainer(
    overrides: [
      jobDashboardRepositoryProvider.overrideWith((ref) => fake),
    ],
  );
  if (initialFilter != null) {
    container.read(exceptionsFilterProvider.notifier).state = initialFilter;
  }
  return container;
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

void main() {
  group('exceptionsRowsProvider', () {
    test(
      'T-2.5-P-UNIT-01: failedExports filter calls listJobs(graphics_generate, failed) '
      'and returns response items unchanged',
      () async {
        final failed = [
          _job(id: 'fe-1', status: 'failed'),
          _job(id: 'fe-2', status: 'failed'),
        ];
        final fake = _FakeJobDashboardRepository(
          failedExports: JobListResponse(items: failed, total: failed.length),
        );
        final container = _container(
          fake,
          initialFilter: ExceptionFilter.failedExports,
        );
        addTearDown(container.dispose);

        final result =
            await container.read(exceptionsRowsProvider.future);

        expect(fake.calls, hasLength(1));
        expect(fake.calls.single.jobType, 'graphics_generate');
        expect(fake.calls.single.status, 'failed');
        expect(fake.calls.single.limit, 200);
        expect(result.map((j) => j.id).toList(),
            equals(['fe-1', 'fe-2']));
      },
    );

    test(
      'T-2.5-P-UNIT-02: zombieJobs filter calls listJobs(running) and returns '
      'only Job.isStale==true rows',
      () async {
        final now = DateTime.now();
        final stale1 = _job(
          id: 'z-1',
          status: 'running',
          startedAt: now.subtract(const Duration(minutes: 15)),
        );
        final stale2 = _job(
          id: 'z-2',
          status: 'running',
          startedAt: now.subtract(const Duration(minutes: 30)),
        );
        final stale3 = _job(
          id: 'z-3',
          status: 'running',
          startedAt: now.subtract(const Duration(minutes: 11)),
        );
        final fresh1 = _job(
          id: 'r-1',
          status: 'running',
          startedAt: now.subtract(const Duration(minutes: 2)),
        );
        final fresh2 = _job(
          id: 'r-2',
          status: 'running',
          startedAt: now.subtract(const Duration(minutes: 5)),
        );
        final fake = _FakeJobDashboardRepository(
          running: JobListResponse(
            items: [stale1, stale2, stale3, fresh1, fresh2],
            total: 5,
          ),
        );
        final container = _container(
          fake,
          initialFilter: ExceptionFilter.zombieJobs,
        );
        addTearDown(container.dispose);

        final result =
            await container.read(exceptionsRowsProvider.future);

        expect(fake.calls, hasLength(1));
        expect(fake.calls.single.status, 'running');
        expect(fake.calls.single.jobType, isNull);
        expect(fake.calls.single.limit, 200);
        expect(result.map((j) => j.id).toSet(),
            equals({'z-1', 'z-2', 'z-3'}));
      },
    );

    test(
      'T-2.5-P-UNIT-03: all filter unions failed exports + stale running jobs, '
      'de-dupes by id, sorts by createdAt DESC',
      () async {
        final now = DateTime.now();
        final fe1 = _job(
          id: 'fe-1',
          status: 'failed',
          createdAt: DateTime.utc(2026, 4, 27, 9, 0, 0),
        );
        final fe2 = _job(
          id: 'fe-2',
          status: 'failed',
          createdAt: DateTime.utc(2026, 4, 27, 11, 0, 0),
        );
        final stale1 = _job(
          id: 'z-1',
          status: 'running',
          createdAt: DateTime.utc(2026, 4, 27, 12, 0, 0),
          startedAt: now.subtract(const Duration(minutes: 20)),
        );
        final stale2 = _job(
          id: 'z-2',
          status: 'running',
          createdAt: DateTime.utc(2026, 4, 27, 8, 0, 0),
          startedAt: now.subtract(const Duration(minutes: 12)),
        );
        final stale3 = _job(
          id: 'z-3',
          status: 'running',
          createdAt: DateTime.utc(2026, 4, 27, 10, 0, 0),
          startedAt: now.subtract(const Duration(minutes: 30)),
        );
        final fresh1 = _job(
          id: 'r-1',
          status: 'running',
          startedAt: now.subtract(const Duration(minutes: 1)),
        );
        final fresh2 = _job(
          id: 'r-2',
          status: 'running',
          startedAt: now.subtract(const Duration(minutes: 4)),
        );
        final fake = _FakeJobDashboardRepository(
          failedExports: JobListResponse(items: [fe1, fe2], total: 2),
          running: JobListResponse(
            items: [stale1, stale2, stale3, fresh1, fresh2],
            total: 5,
          ),
        );
        final container = _container(
          fake,
          initialFilter: ExceptionFilter.all,
        );
        addTearDown(container.dispose);

        final result =
            await container.read(exceptionsRowsProvider.future);

        expect(fake.calls, hasLength(2));
        final byTypeStatus = fake.calls
            .map((c) => '${c.jobType ?? "_"}|${c.status ?? "_"}')
            .toList();
        expect(
          byTypeStatus,
          equals(['graphics_generate|failed', '_|running']),
          reason: 'failed-exports query must precede running query (sequential, '
              'matches exceptionsRowsProvider.all branch order).',
        );
        // 2 failed + 3 stale = 5 unique rows, fresh runners excluded.
        expect(result, hasLength(5));
        expect(
          result.map((j) => j.id).toList(),
          equals(['z-1', 'fe-2', 'z-3', 'fe-1', 'z-2']),
          reason: 'merged list sorted by createdAt DESC: '
              'z-1 (12:00) > fe-2 (11:00) > z-3 (10:00) > '
              'fe-1 (09:00) > z-2 (08:00)',
        );
      },
    );
  });
}
