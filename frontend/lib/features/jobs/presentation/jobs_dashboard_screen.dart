import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/routing/app_drawer.dart';
import '../../../core/theme/app_theme.dart';
import '../application/jobs_providers.dart';
import '../data/job_dashboard_repository.dart';
import '../domain/job.dart';
import 'widgets/job_card.dart';
import 'widgets/job_detail_sheet.dart';
import 'widgets/jobs_stats_bar.dart';

class JobsDashboardScreen extends ConsumerStatefulWidget {
  const JobsDashboardScreen({super.key});

  @override
  ConsumerState<JobsDashboardScreen> createState() =>
      _JobsDashboardScreenState();
}

class _JobsDashboardScreenState extends ConsumerState<JobsDashboardScreen> {
  SummaTheme get _theme => Theme.of(context).extension<SummaTheme>()!;

  @override
  void initState() {
    super.initState();
  }

  static const _jobTypes = <String?, String>{
    null: 'All Types',
    'catalog_sync': 'Catalog Sync',
    'cube_fetch': 'Data Fetch',
    'graphics_generate': 'Chart Generation',
  };

  static const _statuses = <String?, String>{
    null: 'All',
    'queued': 'Queued',
    'running': 'Running',
    'success': 'Success',
    'failed': 'Failed',
  };

  Future<void> _retryJob(Job job) async {
    try {
      final repo = ref.read(jobDashboardRepositoryProvider);
      final newJobId = await repo.retryJob(job.id);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Job retried (new job: $newJobId)')),
        );
        ref.invalidate(jobsListProvider);
      }
    } on DioException catch (e) {
      if (mounted) {
        final message = e.response?.statusCode == 409
            ? 'Job is not retryable'
            : 'Retry failed: ${e.message}';
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(message)),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    // Activate auto-refresh
    ref.watch(autoRefreshProvider);

    final filter = ref.watch(jobFilterProvider);
    final jobsAsync = ref.watch(jobsListProvider);

    return Scaffold(
      drawer: const AppDrawer(),
      appBar: AppBar(
        title: const Text('Jobs Dashboard'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Refresh jobs',
            onPressed: () => ref.invalidate(jobsListProvider),
          ),
        ],
      ),
      body: Column(
        children: [
          // Stats bar
          jobsAsync.whenOrNull(
                data: (response) => Padding(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                  child: JobsStatsBar(
                    jobs: response.items,
                    onStatusTap: (status) {
                      ref.read(jobFilterProvider.notifier).state =
                          filter.copyWith(status: status);
                    },
                  ),
                ),
              ) ??
              const SizedBox.shrink(),

          // Filter bar
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            child: Row(
              children: [
                // Job type dropdown
                Expanded(
                  child: DropdownButtonFormField<String?>(
                    value: filter.jobType,
                    decoration: InputDecoration(
                      labelText: 'Job Type',
                      labelStyle:
                          TextStyle(color: _theme.textSecondary),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(8),
                      ),
                      contentPadding: const EdgeInsets.symmetric(
                        horizontal: 12,
                        vertical: 8,
                      ),
                    ),
                    dropdownColor: _theme.bgSurface,
                    style: TextStyle(color: _theme.textPrimary),
                    items: _jobTypes.entries
                        .map(
                          (e) => DropdownMenuItem(
                            value: e.key,
                            child: Text(e.value),
                          ),
                        )
                        .toList(),
                    onChanged: (value) {
                      ref.read(jobFilterProvider.notifier).state =
                          filter.copyWith(jobType: value);
                    },
                  ),
                ),
                const SizedBox(width: 12),

                // Status filter chips
                Expanded(
                  child: SingleChildScrollView(
                    scrollDirection: Axis.horizontal,
                    child: Row(
                      children: _statuses.entries.map((e) {
                        final isSelected = filter.status == e.key;
                        return Padding(
                          padding: const EdgeInsets.only(right: 6),
                          child: ChoiceChip(
                            label: Text(e.value),
                            selected: isSelected,
                            selectedColor:
                                _theme.accent.withOpacity(0.2),
                            labelStyle: TextStyle(
                              color: isSelected
                                  ? _theme.accent
                                  : _theme.textSecondary,
                              fontSize: 12,
                            ),
                            onSelected: (_) {
                              ref.read(jobFilterProvider.notifier).state =
                                  filter.copyWith(status: e.key);
                            },
                          ),
                        );
                      }).toList(),
                    ),
                  ),
                ),
              ],
            ),
          ),

          // Total count
          jobsAsync.whenOrNull(
                data: (response) => Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  child: Align(
                    alignment: Alignment.centerLeft,
                    child: Text(
                      '${response.total} jobs',
                      style: TextStyle(
                        color: _theme.textSecondary,
                        fontSize: 13,
                      ),
                    ),
                  ),
                ),
              ) ??
              const SizedBox.shrink(),

          const SizedBox(height: 8),

          // Jobs list
          Expanded(
            child: jobsAsync.when(
              loading: () =>
                  const Center(child: CircularProgressIndicator()),
              error: (err, stack) => Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.error_outline,
                        color: _theme.destructive, size: 48),
                    const SizedBox(height: 16),
                    Text(
                      'Failed to load jobs\n$err',
                      textAlign: TextAlign.center,
                      style:
                          TextStyle(color: _theme.textSecondary),
                    ),
                    const SizedBox(height: 16),
                    ElevatedButton(
                      onPressed: () =>
                          ref.invalidate(jobsListProvider),
                      child: const Text('Retry'),
                    ),
                  ],
                ),
              ),
              data: (response) {
                if (response.items.isEmpty) {
                  return Center(
                    child: Text(
                      'No jobs found. Adjust filters or wait for new jobs.',
                      textAlign: TextAlign.center,
                      style: TextStyle(color: _theme.textSecondary),
                    ),
                  );
                }

                return ListView.separated(
                  padding: const EdgeInsets.all(16),
                  itemCount: response.items.length,
                  separatorBuilder: (_, __) =>
                      const SizedBox(height: 12),
                  itemBuilder: (context, index) {
                    final job = response.items[index];
                    return JobCard(
                      job: job,
                      onRetry: () => _retryJob(job),
                      onViewDetail: () =>
                          showJobDetailSheet(context, job),
                    );
                  },
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}
