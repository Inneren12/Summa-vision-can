import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../domain/job.dart';
import '../../application/jobs_providers.dart';
import 'job_detail_sheet.dart';

class JobCard extends ConsumerWidget {
  final Job job;

  const JobCard({super.key, required this.job});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                _buildStatusBadge(),
                const SizedBox(width: 12),
                Text(
                  job.jobTypeDisplay,
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const Spacer(),
                if (job.duration != null)
                  Text(
                    '${job.duration!.inMinutes}m ${job.duration!.inSeconds % 60}s elapsed',
                  )
                else if (job.startedAt != null)
                  Text(
                    '${DateTime.now().difference(job.startedAt!).inMinutes}m elapsed',
                  ),
              ],
            ),
            const SizedBox(height: 12),
            Text('Created: ${job.createdAt} by ${job.createdBy ?? 'unknown'}'),
            const SizedBox(height: 4),
            Text(
              'Attempts: ${job.attemptCount}/${job.maxAttempts}',
              style: TextStyle(
                color: job.attemptCount > 1 ? Colors.amber : null,
                fontWeight: job.attemptCount > 1 ? FontWeight.bold : null,
              ),
            ),
            if (job.dedupeKey != null) ...[
              const SizedBox(height: 4),
              Tooltip(
                message: job.dedupeKey!,
                child: Text(
                  'Dedupe: ${job.dedupeKey!.length > 40 ? job.dedupeKey!.substring(0, 40) + '...' : job.dedupeKey!}',
                ),
              ),
            ],

            if (job.isStale) ...[
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.all(8),
                color: Colors.amber.withOpacity(0.2),
                child: Row(
                  children: [
                    const Icon(Icons.warning, color: Colors.amber),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        '⚠ Running for ${DateTime.now().difference(job.startedAt!).inMinutes} minutes — may be stale',
                        style: const TextStyle(
                          color: Colors.amber,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],

            if (job.status == 'failed') ...[
              const SizedBox(height: 8),
              Text(
                'Error: ${job.errorCode ?? 'UNKNOWN'} - ${job.errorMessage != null && job.errorMessage!.length > 100 ? job.errorMessage!.substring(0, 100) + '...' : job.errorMessage}',
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
            ],

            const SizedBox(height: 16),
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                if (job.isRetryable)
                  TextButton(
                    onPressed: () => _handleRetry(context, ref),
                    child: const Text('RETRY'),
                  ),
                const SizedBox(width: 8),
                TextButton(
                  onPressed: () => _showDetailSheet(context),
                  child: const Text('VIEW DETAIL'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildStatusBadge() {
    Color badgeColor;
    switch (job.status) {
      case 'queued':
        badgeColor = Colors.grey;
        break;
      case 'running':
        badgeColor = Colors.blue;
        break;
      case 'success':
        badgeColor = Colors.green;
        break;
      case 'failed':
        badgeColor = Colors.red;
        break;
      case 'cancelled':
      default:
        badgeColor = Colors.grey.shade700;
        break;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: badgeColor.withOpacity(0.2),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: badgeColor),
      ),
      child: Text(
        job.statusDisplay,
        style: TextStyle(
          color: badgeColor,
          fontWeight: FontWeight.bold,
          fontSize: 12,
        ),
      ),
    );
  }

  Future<void> _handleRetry(BuildContext context, WidgetRef ref) async {
    final repo = ref.read(jobDashboardRepositoryProvider);
    try {
      final newJobId = await repo.retryJob(job.id);
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Job retried (new job: $newJobId)')),
        );
      }
      ref.invalidate(jobsListProvider);
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to retry: Job is not retryable')),
        );
      }
    }
  }

  void _showDetailSheet(BuildContext context) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (_) => JobDetailSheet(job: job),
    );
  }
}
