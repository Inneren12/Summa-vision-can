import 'dart:convert';

import 'package:flutter/material.dart';

import '../../../../core/theme/app_theme.dart';
import '../../domain/job.dart';

/// Shows full job detail in a bottom sheet.
void showJobDetailSheet(BuildContext context, Job job) {
  showModalBottomSheet(
    context: context,
    isScrollControlled: true,
    backgroundColor: AppTheme.surfaceDark,
    shape: const RoundedRectangleBorder(
      borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
    ),
    builder: (_) => JobDetailSheet(job: job),
  );
}

class JobDetailSheet extends StatelessWidget {
  const JobDetailSheet({super.key, required this.job});
  final Job job;

  String _formatIso(DateTime? dt) =>
      dt?.toIso8601String() ?? '—';

  String? _prettyJson(String? raw) {
    if (raw == null) return null;
    try {
      final parsed = jsonDecode(raw);
      return const JsonEncoder.withIndent('  ').convert(parsed);
    } catch (_) {
      return raw;
    }
  }

  @override
  Widget build(BuildContext context) {
    final resultJson = _prettyJson(job.resultJson);
    final payloadJson = _prettyJson(job.payloadJson);

    // Check if this is a graphics_generate job with a CDN URL
    String? cdnUrl;
    if (job.jobType == 'graphics_generate' && job.resultJson != null) {
      try {
        final parsed = jsonDecode(job.resultJson!) as Map<String, dynamic>;
        cdnUrl = parsed['cdn_url_lowres'] as String?;
      } catch (_) {}
    }

    return DraggableScrollableSheet(
      initialChildSize: 0.75,
      minChildSize: 0.4,
      maxChildSize: 0.95,
      expand: false,
      builder: (context, scrollController) {
        return ListView(
          controller: scrollController,
          padding: const EdgeInsets.all(20),
          children: [
            // Drag handle
            Center(
              child: Container(
                width: 40,
                height: 4,
                margin: const EdgeInsets.only(bottom: 16),
                decoration: BoxDecoration(
                  color: AppTheme.textSecondary.withOpacity(0.4),
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),

            Text(
              'Job Detail',
              style: const TextStyle(
                color: AppTheme.textPrimary,
                fontSize: 20,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 16),

            _DetailRow('ID', job.id),
            _DetailRow('Type', job.jobTypeDisplay),
            _DetailRow('Status', job.statusDisplay),
            _DetailRow('Attempts', '${job.attemptCount}/${job.maxAttempts}'),
            _DetailRow('Created At', _formatIso(job.createdAt)),
            _DetailRow('Started At', _formatIso(job.startedAt)),
            _DetailRow('Finished At', _formatIso(job.finishedAt)),
            _DetailRow('Created By', job.createdBy ?? '—'),
            _DetailRow('Dedupe Key', job.dedupeKey ?? '—'),

            if (job.errorCode != null)
              _DetailRow('Error Code', job.errorCode!),
            if (job.errorMessage != null) ...[
              const SizedBox(height: 12),
              const Text(
                'Error Message',
                style: TextStyle(
                  color: AppTheme.textSecondary,
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 4),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: AppTheme.errorRed.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  job.errorMessage!,
                  style: TextStyle(
                    color: AppTheme.errorRed,
                    fontSize: 13,
                    fontFamily: 'monospace',
                  ),
                ),
              ),
            ],

            if (payloadJson != null) ...[
              const SizedBox(height: 16),
              const Text(
                'Payload',
                style: TextStyle(
                  color: AppTheme.textSecondary,
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 4),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: AppTheme.backgroundDark,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: SelectableText(
                  payloadJson,
                  style: const TextStyle(
                    color: AppTheme.neonGreen,
                    fontSize: 12,
                    fontFamily: 'monospace',
                  ),
                ),
              ),
            ],

            if (resultJson != null) ...[
              const SizedBox(height: 16),
              const Text(
                'Result',
                style: TextStyle(
                  color: AppTheme.textSecondary,
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 4),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: AppTheme.backgroundDark,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: SelectableText(
                  resultJson,
                  style: const TextStyle(
                    color: AppTheme.neonBlue,
                    fontSize: 12,
                    fontFamily: 'monospace',
                  ),
                ),
              ),
            ],

            if (cdnUrl != null) ...[
              const SizedBox(height: 16),
              ElevatedButton.icon(
                onPressed: () {
                  // In a real app, this would navigate to the CDN URL
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(content: Text('CDN URL: $cdnUrl')),
                  );
                },
                icon: const Icon(Icons.image),
                label: const Text('View Publication'),
              ),
            ],

            const SizedBox(height: 24),
          ],
        );
      },
    );
  }
}

class _DetailRow extends StatelessWidget {
  const _DetailRow(this.label, this.value);
  final String label;
  final String value;

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
                color: AppTheme.textSecondary,
                fontSize: 13,
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
          Expanded(
            child: SelectableText(
              value,
              style: const TextStyle(
                color: AppTheme.textPrimary,
                fontSize: 13,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
