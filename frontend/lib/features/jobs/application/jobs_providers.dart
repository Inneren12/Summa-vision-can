import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/dio_client.dart';
import '../data/job_dashboard_repository.dart';
import '../domain/job_filter.dart';
import '../domain/job_list_response.dart';

final jobDashboardRepositoryProvider = Provider<JobDashboardRepository>((ref) {
  return JobDashboardRepository(ref.watch(dioProvider));
});

final jobFilterProvider = StateProvider<JobFilter>((ref) => const JobFilter());

final jobsListProvider = FutureProvider.autoDispose<JobListResponse>((
  ref,
) async {
  final filter = ref.watch(jobFilterProvider);
  final repo = ref.read(jobDashboardRepositoryProvider);
  return repo.listJobs(
    jobType: filter.jobType,
    status: filter.status,
    limit: filter.limit,
  );
});

final autoRefreshProvider = Provider.autoDispose<void>((ref) {
  final timer = Timer.periodic(const Duration(seconds: 10), (_) {
    ref.invalidate(jobsListProvider);
  });
  ref.onDispose(timer.cancel);
});
