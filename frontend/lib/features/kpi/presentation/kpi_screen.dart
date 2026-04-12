import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/routing/app_drawer.dart';
import '../../../core/theme/app_theme.dart';
import '../application/kpi_providers.dart';
import '../domain/kpi_data.dart';
import 'widgets/download_funnel.dart';
import 'widgets/job_failure_chart.dart';
import 'widgets/kpi_summary_cards.dart';
import 'widgets/lead_breakdown.dart';

/// KPI dashboard screen — single-page view of all key business metrics.
///
/// Route: `/kpi`.
/// Auto-refreshes every 60 seconds.
class KPIScreen extends ConsumerStatefulWidget {
  const KPIScreen({super.key});

  @override
  ConsumerState<KPIScreen> createState() => _KPIScreenState();
}

class _KPIScreenState extends ConsumerState<KPIScreen> {
  Timer? _refreshTimer;

  @override
  void initState() {
    super.initState();
    _refreshTimer = Timer.periodic(
      const Duration(seconds: 60),
      (_) => ref.invalidate(kpiDataProvider),
    );
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final kpiAsync = ref.watch(kpiDataProvider);
    final selectedDays = ref.watch(kpiPeriodDaysProvider);

    return Scaffold(
      drawer: const AppDrawer(),
      appBar: AppBar(
        title: const Text('KPI Dashboard'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Refresh KPIs',
            onPressed: () => ref.invalidate(kpiDataProvider),
          ),
        ],
      ),
      body: kpiAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (err, stack) => Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.error_outline,
                  color: AppTheme.errorRed, size: 48),
              const SizedBox(height: 16),
              Text(
                'Failed to load KPIs\n$err',
                textAlign: TextAlign.center,
                style: const TextStyle(color: AppTheme.textSecondary),
              ),
              const SizedBox(height: 16),
              ElevatedButton(
                onPressed: () => ref.invalidate(kpiDataProvider),
                child: const Text('Retry'),
              ),
            ],
          ),
        ),
        data: (data) => _KPIBody(
          data: data,
          selectedDays: selectedDays,
          onPeriodChanged: (days) =>
              ref.read(kpiPeriodDaysProvider.notifier).state = days,
        ),
      ),
    );
  }
}

class _KPIBody extends StatelessWidget {
  const _KPIBody({
    required this.data,
    required this.selectedDays,
    required this.onPeriodChanged,
  });

  final KPIData data;
  final int selectedDays;
  final ValueChanged<int> onPeriodChanged;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        // A) Period Selector
        _PeriodSelector(
          selectedDays: selectedDays,
          onChanged: onPeriodChanged,
        ),
        const SizedBox(height: 16),

        // B) Summary Cards
        KPISummaryCards(data: data),
        const SizedBox(height: 16),

        // C) Download Funnel
        DownloadFunnel(data: data),
        const SizedBox(height: 16),

        // D) Lead Breakdown
        LeadBreakdown(data: data),
        const SizedBox(height: 16),

        // E) Job Failure Breakdown
        JobFailureChart(failedByType: data.failedByType),
        const SizedBox(height: 16),

        // F) System Health
        _SystemHealthRow(data: data),
        const SizedBox(height: 16),

        // G) Footer
        _Footer(periodEnd: data.periodEnd),
      ],
    );
  }
}

/// Period selector — 7, 30, or 90 days.
class _PeriodSelector extends StatelessWidget {
  const _PeriodSelector({
    required this.selectedDays,
    required this.onChanged,
  });

  final int selectedDays;
  final ValueChanged<int> onChanged;

  @override
  Widget build(BuildContext context) {
    return SegmentedButton<int>(
      segments: const [
        ButtonSegment(value: 7, label: Text('7 days')),
        ButtonSegment(value: 30, label: Text('30 days')),
        ButtonSegment(value: 90, label: Text('90 days')),
      ],
      selected: {selectedDays},
      onSelectionChanged: (selected) => onChanged(selected.first),
    );
  }
}

/// Compact system health indicators.
class _SystemHealthRow extends StatelessWidget {
  const _SystemHealthRow({required this.data});

  final KPIData data;

  @override
  Widget build(BuildContext context) {
    final hasViolations = data.dataContractViolations > 0;
    final hasPermanentFailures = data.espFailedPermanentCount > 0;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'System Health',
              style: TextStyle(
                color: AppTheme.textPrimary,
                fontSize: 16,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 24,
              runSpacing: 12,
              children: [
                _HealthChip(
                  icon: Icons.sync,
                  label: 'Catalog Syncs',
                  value: '${data.catalogSyncs}',
                  color: AppTheme.neonBlue,
                ),
                _HealthChip(
                  icon: hasViolations
                      ? Icons.warning_amber_rounded
                      : Icons.check_circle_outline,
                  label: 'Contract Violations',
                  value: '${data.dataContractViolations}',
                  color: hasViolations ? AppTheme.errorRed : AppTheme.neonGreen,
                ),
                _HealthChip(
                  icon: Icons.email_outlined,
                  label: 'ESP Sync',
                  value:
                      '${data.espSyncedCount} synced, ${data.espFailedPermanentCount} failed',
                  color: hasPermanentFailures
                      ? AppTheme.neonYellow
                      : AppTheme.neonGreen,
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _HealthChip extends StatelessWidget {
  const _HealthChip({
    required this.icon,
    required this.label,
    required this.value,
    required this.color,
  });

  final IconData icon;
  final String label;
  final String value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, color: color, size: 18),
        const SizedBox(width: 6),
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              label,
              style: const TextStyle(
                color: AppTheme.textSecondary,
                fontSize: 11,
              ),
            ),
            Text(
              value,
              style: TextStyle(
                color: color,
                fontWeight: FontWeight.bold,
                fontSize: 13,
              ),
            ),
          ],
        ),
      ],
    );
  }
}

class _Footer extends StatelessWidget {
  const _Footer({required this.periodEnd});

  final DateTime periodEnd;

  @override
  Widget build(BuildContext context) {
    final formatted =
        '${periodEnd.year}-${periodEnd.month.toString().padLeft(2, '0')}-'
        '${periodEnd.day.toString().padLeft(2, '0')} '
        '${periodEnd.hour.toString().padLeft(2, '0')}:'
        '${periodEnd.minute.toString().padLeft(2, '0')} UTC';

    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 8),
        child: Text(
          'Last updated: $formatted  \u2022  Auto-refresh: 60s',
          style: const TextStyle(
            color: AppTheme.textSecondary,
            fontSize: 11,
          ),
        ),
      ),
    );
  }
}
