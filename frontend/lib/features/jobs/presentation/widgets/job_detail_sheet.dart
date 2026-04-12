import 'package:flutter/material.dart';
import '../../domain/job.dart';

class JobDetailSheet extends StatelessWidget {
  final Job job;

  const JobDetailSheet({super.key, required this.job});

  @override
  Widget build(BuildContext context) {
    return DraggableScrollableSheet(
      initialChildSize: 0.8,
      minChildSize: 0.5,
      maxChildSize: 0.95,
      expand: false,
      builder: (context, scrollController) {
        return Container(
          padding: const EdgeInsets.all(16),
          child: ListView(
            controller: scrollController,
            children: [
              Text(
                'Job Details',
                style: Theme.of(context).textTheme.headlineSmall,
              ),
              const Divider(),
              _DetailRow(label: 'ID', value: job.id),
              _DetailRow(label: 'Type', value: job.jobType),
              _DetailRow(label: 'Status', value: job.status),
              _DetailRow(
                label: 'Created At',
                value: job.createdAt.toIso8601String(),
              ),
              _DetailRow(
                label: 'Started At',
                value: job.startedAt?.toIso8601String() ?? '-',
              ),
              _DetailRow(
                label: 'Finished At',
                value: job.finishedAt?.toIso8601String() ?? '-',
              ),
              _DetailRow(
                label: 'Attempts',
                value: '${job.attemptCount} / ${job.maxAttempts}',
              ),
              if (job.dedupeKey != null)
                _DetailRow(label: 'Dedupe Key', value: job.dedupeKey!),
              if (job.errorCode != null)
                _DetailRow(label: 'Error Code', value: job.errorCode!),

              const SizedBox(height: 16),
              const Text(
                'Payload JSON:',
                style: TextStyle(fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              Container(
                padding: const EdgeInsets.all(8),
                color: Theme.of(context).colorScheme.surfaceVariant,
                child: SelectableText(
                  job.payloadJson ?? '{}',
                  style: const TextStyle(fontFamily: 'monospace', fontSize: 12),
                ),
              ),

              if (job.resultJson != null) ...[
                const SizedBox(height: 16),
                const Text(
                  'Result JSON:',
                  style: TextStyle(fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 8),
                Container(
                  padding: const EdgeInsets.all(8),
                  color: Theme.of(context).colorScheme.surfaceVariant,
                  child: SelectableText(
                    job.resultJson!,
                    style: const TextStyle(
                      fontFamily: 'monospace',
                      fontSize: 12,
                    ),
                  ),
                ),
                if (job.jobType == 'graphics_generate')
                  Padding(
                    padding: const EdgeInsets.only(top: 16),
                    child: ElevatedButton(
                      onPressed: () {
                        // In a real app, parse URL from result_json and launch it.
                      },
                      child: const Text('View Publication'),
                    ),
                  ),
              ],

              if (job.errorMessage != null) ...[
                const SizedBox(height: 16),
                const Text(
                  'Error Message:',
                  style: TextStyle(
                    fontWeight: FontWeight.bold,
                    color: Colors.red,
                  ),
                ),
                const SizedBox(height: 8),
                Container(
                  padding: const EdgeInsets.all(8),
                  color: Colors.red.withOpacity(0.1),
                  child: SelectableText(
                    job.errorMessage!,
                    style: const TextStyle(
                      color: Colors.red,
                      fontFamily: 'monospace',
                      fontSize: 12,
                    ),
                  ),
                ),
              ],
            ],
          ),
        );
      },
    );
  }
}

class _DetailRow extends StatelessWidget {
  final String label;
  final String value;

  const _DetailRow({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 100,
            child: Text(
              label,
              style: const TextStyle(
                fontWeight: FontWeight.bold,
                color: Colors.grey,
              ),
            ),
          ),
          Expanded(child: SelectableText(value)),
        ],
      ),
    );
  }
}
