import 'package:flutter/material.dart';

import '../../../../core/theme/app_theme.dart';
import '../../domain/kpi_data.dart';

/// Visual breakdown of leads by category (B2B, Education, ISP, B2C).
///
/// Uses proportional Container bars instead of a charting library.
class LeadBreakdown extends StatelessWidget {
  const LeadBreakdown({super.key, required this.data});

  final KPIData data;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context).extension<SummaTheme>()!;
    final segments = [
      _Segment('B2B', data.b2bLeads, theme.dataGov),
      _Segment('Education', data.educationLeads, theme.dataSociety),
      _Segment('ISP', data.ispLeads, theme.dataBaseline),
      _Segment('B2C', data.b2cLeads, theme.textMuted),
    ];

    final total = data.totalLeads.clamp(1, 1 << 30);

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Lead Breakdown',
              style: TextStyle(
                color: theme.textPrimary,
                fontSize: 16,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 16),
            // Stacked horizontal bar
            ClipRRect(
              borderRadius: BorderRadius.circular(6),
              child: SizedBox(
                height: 28,
                child: Row(
                  children: [
                    for (final seg in segments)
                      if (seg.count > 0)
                        Expanded(
                          flex: seg.count,
                          child: Container(
                            color: seg.color.withOpacity(0.6),
                          ),
                        ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),
            // Legend
            for (final seg in segments) ...[
              _LegendRow(
                segment: seg,
                total: total,
              ),
              const SizedBox(height: 6),
            ],
          ],
        ),
      ),
    );
  }
}

class _Segment {
  const _Segment(this.label, this.count, this.color);

  final String label;
  final int count;
  final Color color;
}

class _LegendRow extends StatelessWidget {
  const _LegendRow({required this.segment, required this.total});

  final _Segment segment;
  final int total;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context).extension<SummaTheme>()!;
    final pct = (segment.count / total * 100).toStringAsFixed(1);
    return Row(
      children: [
        Container(
          width: 12,
          height: 12,
          decoration: BoxDecoration(
            color: segment.color,
            borderRadius: BorderRadius.circular(2),
          ),
        ),
        const SizedBox(width: 8),
        Text(
          segment.label,
          style: TextStyle(
            color: segment.label == 'B2B'
                ? theme.textPrimary
                : theme.textSecondary,
            fontWeight:
                segment.label == 'B2B' ? FontWeight.bold : FontWeight.normal,
            fontSize: 13,
          ),
        ),
        const Spacer(),
        Text(
          '${segment.count}',
          style: TextStyle(
            color: segment.color,
            fontWeight: FontWeight.bold,
            fontSize: 13,
          ),
        ),
        const SizedBox(width: 8),
        Text(
          '$pct%',
          style: TextStyle(
            color: theme.textSecondary,
            fontSize: 12,
          ),
        ),
      ],
    );
  }
}
