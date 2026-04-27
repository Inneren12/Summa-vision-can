import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../jobs/data/job_dashboard_repository.dart';
import '../../jobs/domain/job.dart';
import '../domain/exception_filter.dart';

/// Currently selected filter chip on the /exceptions screen.
final exceptionsFilterProvider = StateProvider<ExceptionFilter>(
  (ref) => ExceptionFilter.all,
);

/// Rows to render on /exceptions, derived from the active filter.
///
/// v1 surface (per phase-2-5 recon-proper):
///   - failedExports → GET /admin/jobs?status=failed&job_type=graphics_generate
///   - zombieJobs    → GET /admin/jobs?status=running, then client-side
///                     filter by Job.isStale (10-min threshold mirrored from
///                     the backend reaper).
///   - all           → union of the above, de-duped by job id, sorted by
///                     createdAt DESC.
final exceptionsRowsProvider =
    FutureProvider.autoDispose<List<Job>>((ref) async {
  final filter = ref.watch(exceptionsFilterProvider);
  final repo = ref.read(jobDashboardRepositoryProvider);

  switch (filter) {
    case ExceptionFilter.failedExports:
      final response = await repo.listJobs(
        jobType: 'graphics_generate',
        status: 'failed',
        limit: 200,
      );
      return response.items;

    case ExceptionFilter.zombieJobs:
      final response = await repo.listJobs(
        status: 'running',
        limit: 200,
      );
      // Source of truth is backend reaper threshold (10 min, R8).
      // Frontend mirrors via Job.isStale until backend exposes
      // is_zombie/stale_reason on Job model. See DEBT-040 for tracking.
      return response.items.where((j) => j.isStale).toList();

    case ExceptionFilter.all:
      final results = await Future.wait([
        repo.listJobs(jobType: 'graphics_generate', status: 'failed', limit: 200),
        repo.listJobs(status: 'running', limit: 200),
      ]);
      final failedExports = results[0];
      final running = results[1];
      final zombies = running.items.where((j) => j.isStale).toList();

      final byId = <String, Job>{};
      for (final j in failedExports.items) {
        byId[j.id] = j;
      }
      for (final j in zombies) {
        byId[j.id] = j;
      }
      final merged = byId.values.toList()
        ..sort((a, b) => b.createdAt.compareTo(a.createdAt));
      return merged;
  }
});
