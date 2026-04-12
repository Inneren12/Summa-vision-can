import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../application/jobs_providers.dart';
import 'widgets/job_card.dart';
import 'widgets/jobs_stats_bar.dart';

class JobsDashboardScreen extends ConsumerWidget {
  const JobsDashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // Start auto-refresh timer while this screen is active
    ref.watch(autoRefreshProvider);

    final jobsAsync = ref.watch(jobsListProvider);
    final filter = ref.watch(jobFilterProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Jobs Dashboard'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () {
              ref.invalidate(jobsListProvider);
            },
            tooltip: 'Manual Refresh',
          ),
        ],
      ),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(16.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                if (jobsAsync.hasValue)
                  JobsStatsBar(jobs: jobsAsync.value!.items),
                const SizedBox(height: 16),
                _buildFilterBar(context, ref, filter, jobsAsync),
              ],
            ),
          ),
          Expanded(
            child: jobsAsync.when(
              data: (response) {
                if (response.items.isEmpty) {
                  return const Center(
                    child: Text(
                      'No jobs found. Adjust filters or wait for new jobs.',
                    ),
                  );
                }
                return ListView.builder(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 16,
                    vertical: 8,
                  ),
                  itemCount: response.items.length,
                  itemBuilder: (context, index) {
                    final job = response.items[index];
                    return JobCard(job: job);
                  },
                );
              },
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (error, stack) => Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      'Error: $error',
                      style: TextStyle(
                        color: Theme.of(context).colorScheme.error,
                      ),
                    ),
                    const SizedBox(height: 16),
                    ElevatedButton(
                      onPressed: () => ref.invalidate(jobsListProvider),
                      child: const Text('Retry'),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildFilterBar(
    BuildContext context,
    WidgetRef ref,
    filter,
    AsyncValue jobsAsync,
  ) {
    return Row(
      children: [
        DropdownButton<String?>(
          value: filter.jobType,
          hint: const Text('All Types'),
          items: const [
            DropdownMenuItem(value: null, child: Text('All Types')),
            DropdownMenuItem(
              value: 'catalog_sync',
              child: Text('Catalog Sync'),
            ),
            DropdownMenuItem(value: 'cube_fetch', child: Text('Data Fetch')),
            DropdownMenuItem(
              value: 'graphics_generate',
              child: Text('Chart Generation'),
            ),
          ],
          onChanged: (val) {
            ref.read(jobFilterProvider.notifier).state = filter.copyWith(
              jobType: val,
            );
          },
        ),
        const SizedBox(width: 16),
        Expanded(
          child: SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: [
                SegmentedButton<String?>(
                  segments: const [
                    ButtonSegment(value: null, label: Text('All')),
                    ButtonSegment(value: 'queued', label: Text('Queued')),
                    ButtonSegment(value: 'running', label: Text('Running')),
                    ButtonSegment(value: 'success', label: Text('Success')),
                    ButtonSegment(value: 'failed', label: Text('Failed')),
                  ],
                  selected: {filter.status},
                  onSelectionChanged: (Set<String?> selection) {
                    ref.read(jobFilterProvider.notifier).state = filter.copyWith(
                      status: selection.first,
                    );
                  },
                ),
                const SizedBox(width: 16),
                if (jobsAsync.hasValue) Text('${jobsAsync.value!.total} jobs'),
              ],
            ),
          ),
        ),
      ],
    );
  }
}
