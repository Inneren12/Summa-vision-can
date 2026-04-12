import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../application/jobs_providers.dart';
import '../../domain/job.dart';

class JobsStatsBar extends StatelessWidget {
  final List<Job> jobs;

  const JobsStatsBar({super.key, required this.jobs});

  @override
  Widget build(BuildContext context) {
    int queued = 0;
    int running = 0;
    int success = 0;
    int failed = 0;
    int stale = 0;

    for (final job in jobs) {
      if (job.status == 'queued') queued++;
      if (job.status == 'running') {
        running++;
        if (job.isStale) stale++;
      }
      if (job.status == 'success') success++;
      if (job.status == 'failed') failed++;
    }

    return Container(
      padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 16),
      decoration: BoxDecoration(
        color: Theme.of(context).cardColor,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceEvenly,
        children: [
          _StatItem(label: 'Queued', value: 'queued', count: queued),
          _StatItem(label: 'Running', value: 'running', count: running),
          _StatItem(label: 'Success', value: 'success', count: success, color: Colors.green),
          _StatItem(label: 'Failed', value: 'failed', count: failed, color: Colors.red),
          _StatItem(label: 'Stale', value: 'running', count: stale, color: Colors.amber),
        ],
      ),
    );
  }
}

class _StatItem extends ConsumerWidget {
  final String label;
  final String value;
  final int count;
  final Color? color;

  const _StatItem({
    required this.label,
    required this.value,
    required this.count,
    this.color,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return InkWell(
      onTap: () {
        final filter = ref.read(jobFilterProvider);
        ref.read(jobFilterProvider.notifier).state = filter.copyWith(status: value);
      },
      borderRadius: BorderRadius.circular(8),
      child: Padding(
        padding: const EdgeInsets.all(8.0),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              count.toString(),
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                color: color ?? Theme.of(context).colorScheme.onSurface,
                fontWeight: FontWeight.bold,
              ),
            ),
            Text(
              label,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Colors.grey),
            ),
          ],
        ),
      ),
    );
  }
}
