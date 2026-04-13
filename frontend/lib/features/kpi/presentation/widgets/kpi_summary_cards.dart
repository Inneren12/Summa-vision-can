import 'package:flutter/material.dart';

import '../../../../core/theme/app_theme.dart';
import '../../domain/kpi_data.dart';

/// Four headline metric cards for the KPI dashboard.
class KPISummaryCards extends StatelessWidget {
  const KPISummaryCards({super.key, required this.data});

  final KPIData data;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context).extension<SummaTheme>()!;
    final conversionRate = data.emailsSent > 0
        ? (data.tokensActivated / data.emailsSent * 100)
        : 0.0;

    final totalResolved = data.jobsSucceeded + data.jobsFailed;
    final successRate =
        totalResolved > 0 ? (data.jobsSucceeded / totalResolved * 100) : 0.0;

    return LayoutBuilder(
      builder: (context, constraints) {
        final crossCount = constraints.maxWidth > 800 ? 4 : 2;
        return GridView.count(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          crossAxisCount: crossCount,
          childAspectRatio: 1.6,
          mainAxisSpacing: 12,
          crossAxisSpacing: 12,
          children: [
            _MetricCard(
              label: 'Published',
              value: '${data.publishedCount}',
              subtitle: '+${data.draftCount} drafts',
              accentColor: theme.accent,
            ),
            _MetricCard(
              label: 'Leads',
              value: '${data.totalLeads}',
              subtitle: '${data.b2bLeads} B2B',
              accentColor: theme.dataGov,
            ),
            _MetricCard(
              label: 'Downloads',
              value: '${data.tokensActivated}',
              subtitle: data.emailsSent > 0
                  ? 'of ${data.emailsSent} sent (${conversionRate.toStringAsFixed(1)}%)'
                  : 'N/A',
              accentColor: theme.dataWarning,
            ),
            _MetricCard(
              label: 'Job Success',
              value: totalResolved > 0
                  ? '${successRate.toStringAsFixed(1)}%'
                  : 'N/A',
              subtitle: totalResolved > 0
                  ? '${data.jobsSucceeded}/${totalResolved}'
                  : 'No jobs',
              accentColor: theme.dataNegative,
            ),
          ],
        );
      },
    );
  }
}

class _MetricCard extends StatelessWidget {
  const _MetricCard({
    required this.label,
    required this.value,
    required this.subtitle,
    required this.accentColor,
  });

  final String label;
  final String value;
  final String subtitle;
  final Color accentColor;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context).extension<SummaTheme>()!;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(
              label,
              style: TextStyle(
                color: theme.textSecondary,
                fontSize: 13,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              value,
              style: TextStyle(
                color: accentColor,
                fontSize: 28,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              subtitle,
              style: TextStyle(
                color: theme.textSecondary,
                fontSize: 12,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
