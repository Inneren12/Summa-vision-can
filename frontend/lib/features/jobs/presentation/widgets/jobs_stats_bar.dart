import 'package:flutter/material.dart';

import '../../../../core/theme/app_theme.dart';
import '../../domain/job.dart';

/// Compact summary stats bar showing job status counts.
class JobsStatsBar extends StatelessWidget {
  const JobsStatsBar({
    super.key,
    required this.jobs,
    required this.onStatusTap,
  });

  final List<Job> jobs;

  /// Called when a stat is tapped, passing the status filter value
  /// (or null for "Stale").
  final void Function(String? status) onStatusTap;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context).extension<SummaTheme>()!;
    final queued = jobs.where((j) => j.status == 'queued').length;
    final running = jobs.where((j) => j.status == 'running').length;
    final success = jobs.where((j) => j.status == 'success').length;
    final failed = jobs.where((j) => j.status == 'failed').length;
    final stale = jobs.where((j) => j.isStale).length;

    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: Row(
        children: [
          _StatChip(
            label: 'Queued',
            count: queued,
            color: theme.textMuted,
            onTap: () => onStatusTap('queued'),
          ),
          _divider(theme.textSecondary),
          _StatChip(
            label: 'Running',
            count: running,
            color: theme.dataGov,
            onTap: () => onStatusTap('running'),
          ),
          _divider(theme.textSecondary),
          _StatChip(
            label: 'Success',
            count: success,
            color: theme.dataPositive,
            onTap: () => onStatusTap('success'),
          ),
          _divider(theme.textSecondary),
          _StatChip(
            label: 'Failed',
            count: failed,
            color: theme.destructive,
            onTap: () => onStatusTap('failed'),
          ),
          _divider(theme.textSecondary),
          _StatChip(
            label: 'Stale',
            count: stale,
            color: theme.dataWarning,
            onTap: () => onStatusTap('running'),
          ),
        ],
      ),
    );
  }

  Widget _divider(Color dividerColor) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 4),
      child: Text(
        '|',
        style: TextStyle(
          color: dividerColor.withOpacity(0.4),
          fontSize: 14,
        ),
      ),
    );
  }
}

class _StatChip extends StatelessWidget {
  const _StatChip({
    required this.label,
    required this.count,
    required this.color,
    required this.onTap,
  });

  final String label;
  final int count;
  final Color color;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context).extension<SummaTheme>()!;
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(8),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              '$label: ',
              style: TextStyle(
                color: theme.textSecondary,
                fontSize: 13,
              ),
            ),
            Text(
              '$count',
              style: TextStyle(
                color: color,
                fontSize: 14,
                fontWeight: FontWeight.bold,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
