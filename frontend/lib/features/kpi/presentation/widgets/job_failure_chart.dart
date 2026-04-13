import 'package:flutter/material.dart';

import '../../../../core/theme/app_theme.dart';

/// Horizontal bar chart showing job failures by type.
///
/// If all values are 0 (empty map), shows a "No job failures" message.
class JobFailureChart extends StatelessWidget {
  const JobFailureChart({super.key, required this.failedByType});

  final Map<String, int> failedByType;

  /// Human-readable display name for a job type slug.
  static String _displayName(String type) {
    return type
        .replaceAll('_', ' ')
        .split(' ')
        .map((w) => w.isNotEmpty ? '${w[0].toUpperCase()}${w.substring(1)}' : '')
        .join(' ');
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context).extension<SummaTheme>()!;
    final entries = failedByType.entries.toList()
      ..sort((a, b) => b.value.compareTo(a.value));

    final hasFailures = entries.any((e) => e.value > 0);

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Job Failures by Type',
              style: TextStyle(
                color: theme.textPrimary,
                fontSize: 16,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 16),
            if (!hasFailures)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 24),
                child: Center(
                  child: Text(
                    'No job failures in this period',
                    style: TextStyle(
                      color: theme.dataPositive,
                      fontSize: 14,
                    ),
                  ),
                ),
              )
            else
              for (final entry in entries) ...[
                _FailureBar(
                  label: _displayName(entry.key),
                  count: entry.value,
                  maxCount: entries.first.value.clamp(1, 1 << 30),
                ),
                const SizedBox(height: 8),
              ],
          ],
        ),
      ),
    );
  }
}

class _FailureBar extends StatelessWidget {
  const _FailureBar({
    required this.label,
    required this.count,
    required this.maxCount,
  });

  final String label;
  final int count;
  final int maxCount;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context).extension<SummaTheme>()!;
    final fraction = count / maxCount;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Expanded(
              child: Text(
                label,
                style: TextStyle(
                  color: theme.textSecondary,
                  fontSize: 12,
                ),
              ),
            ),
            Text(
              '$count',
              style: TextStyle(
                color: theme.destructive,
                fontWeight: FontWeight.bold,
                fontSize: 14,
              ),
            ),
          ],
        ),
        const SizedBox(height: 4),
        LayoutBuilder(
          builder: (context, constraints) {
            return Container(
              width: constraints.maxWidth * fraction.clamp(0.05, 1.0),
              height: 20,
              decoration: BoxDecoration(
                color: theme.destructive.withOpacity(0.25),
                borderRadius: BorderRadius.circular(4),
                border: Border.all(color: theme.destructive.withOpacity(0.5)),
              ),
            );
          },
        ),
      ],
    );
  }
}
