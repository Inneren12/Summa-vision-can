import 'package:flutter/material.dart';

import '../../../../core/theme/app_theme.dart';
import '../../domain/kpi_data.dart';

/// Horizontal funnel visualization of the download conversion pipeline.
///
/// Steps: Leads Captured -> Emails Sent -> Tokens Created -> Downloads -> Exhausted
///
/// Uses proportional-width [Container] bars -- no heavy charting dependency.
class DownloadFunnel extends StatelessWidget {
  const DownloadFunnel({super.key, required this.data});

  final KPIData data;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context).extension<SummaTheme>()!;
    final steps = [
      _FunnelStep('Leads Captured', data.totalLeads, theme.accent),
      _FunnelStep('Emails Sent', data.emailsSent, theme.dataGov),
      _FunnelStep('Tokens Created', data.tokensCreated, theme.dataWarning),
      _FunnelStep('Downloads', data.tokensActivated, theme.dataNegative),
      _FunnelStep('Exhausted', data.tokensExhausted, theme.textMuted),
    ];

    final maxVal =
        steps.fold<int>(0, (m, s) => s.count > m ? s.count : m).clamp(1, 1 << 30);

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Download Funnel',
              style: TextStyle(
                color: theme.textPrimary,
                fontSize: 16,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 16),
            for (var i = 0; i < steps.length; i++) ...[
              _FunnelBar(
                step: steps[i],
                maxValue: maxVal,
                previousCount: i > 0 ? steps[i - 1].count : null,
              ),
              if (i < steps.length - 1) const SizedBox(height: 8),
            ],
          ],
        ),
      ),
    );
  }
}

class _FunnelStep {
  const _FunnelStep(this.label, this.count, this.color);

  final String label;
  final int count;
  final Color color;
}

class _FunnelBar extends StatelessWidget {
  const _FunnelBar({
    required this.step,
    required this.maxValue,
    this.previousCount,
  });

  final _FunnelStep step;
  final int maxValue;
  final int? previousCount;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context).extension<SummaTheme>()!;
    final fraction = step.count / maxValue;
    final dropoff = previousCount != null && previousCount! > 0
        ? ((1 - step.count / previousCount!) * 100).toStringAsFixed(0)
        : null;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Expanded(
              child: Text(
                step.label,
                style: TextStyle(
                  color: theme.textSecondary,
                  fontSize: 12,
                ),
              ),
            ),
            Text(
              '${step.count}',
              style: TextStyle(
                color: step.color,
                fontWeight: FontWeight.bold,
                fontSize: 14,
              ),
            ),
            if (dropoff != null) ...[
              const SizedBox(width: 8),
              Text(
                '-$dropoff%',
                style: TextStyle(
                  color: theme.textSecondary,
                  fontSize: 11,
                ),
              ),
            ],
          ],
        ),
        const SizedBox(height: 4),
        LayoutBuilder(
          builder: (context, constraints) {
            return Container(
              width: constraints.maxWidth * fraction.clamp(0.02, 1.0),
              height: 24,
              decoration: BoxDecoration(
                color: step.color.withOpacity(0.25),
                borderRadius: BorderRadius.circular(4),
                border: Border.all(color: step.color.withOpacity(0.5)),
              ),
            );
          },
        ),
      ],
    );
  }
}
