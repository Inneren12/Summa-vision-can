import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/job_dashboard_repository.dart';
import '../domain/job_filter.dart';
import '../domain/job_list_response.dart';

/// Current filter state for the jobs dashboard.
final jobFilterProvider = StateProvider<JobFilter>(
  (ref) => const JobFilter(),
);

/// Fetches the jobs list based on the current filter.
final jobsListProvider =
    FutureProvider.autoDispose<JobListResponse>((ref) async {
  final filter = ref.watch(jobFilterProvider);
  final repo = ref.read(jobDashboardRepositoryProvider);
  return repo.listJobs(
    jobType: filter.jobType,
    status: filter.status,
    limit: filter.limit,
  );
});

/// Auto-refreshes [jobsListProvider] every 10 seconds while active.
final autoRefreshProvider = Provider.autoDispose<void>((ref) {
  final timer = Timer.periodic(const Duration(seconds: 10), (_) {
    ref.invalidate(jobsListProvider);
  });
  ref.onDispose(timer.cancel);
});
