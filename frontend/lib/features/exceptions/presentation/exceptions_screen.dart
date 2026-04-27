import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:summa_vision_admin/l10n/generated/app_localizations.dart';

import '../../../core/routing/app_drawer.dart';
import '../../../core/theme/app_theme.dart';
import '../../jobs/data/job_dashboard_repository.dart';
import '../../jobs/domain/job.dart';
import '../../jobs/presentation/widgets/job_card.dart';
import '../../jobs/presentation/widgets/job_detail_sheet.dart';
import '../application/exceptions_providers.dart';
import '../domain/exception_filter.dart';

class ExceptionsScreen extends ConsumerWidget {
  const ExceptionsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context)!;
    final theme = Theme.of(context).extension<SummaTheme>()!;
    final selectedFilter = ref.watch(exceptionsFilterProvider);
    final asyncRows = ref.watch(exceptionsRowsProvider);

    return Scaffold(
      drawer: const AppDrawer(),
      appBar: AppBar(
        title: Text(l10n.exceptionsTitle),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: l10n.exceptionsRefreshTooltip,
            onPressed: () => ref.invalidate(exceptionsRowsProvider),
          ),
        ],
      ),
      body: Column(
        children: [
          _ExceptionsFilterChips(selected: selectedFilter),
          Expanded(
            child: asyncRows.when(
              loading: () =>
                  const Center(child: CircularProgressIndicator()),
              error: (err, _) => Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.error_outline,
                        color: theme.destructive, size: 48),
                    const SizedBox(height: 16),
                    Text(
                      l10n.exceptionsLoadError(err.toString()),
                      textAlign: TextAlign.center,
                      style: TextStyle(color: theme.textSecondary),
                    ),
                    const SizedBox(height: 16),
                    ElevatedButton(
                      onPressed: () =>
                          ref.invalidate(exceptionsRowsProvider),
                      child: Text(l10n.commonRetryVerb),
                    ),
                  ],
                ),
              ),
              data: (rows) {
                if (rows.isEmpty) {
                  return Center(
                    child: Text(
                      l10n.exceptionsEmptyState,
                      textAlign: TextAlign.center,
                      style: TextStyle(color: theme.textSecondary),
                    ),
                  );
                }
                return ListView.separated(
                  padding: const EdgeInsets.all(16),
                  itemCount: rows.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 12),
                  itemBuilder: (context, index) {
                    final job = rows[index];
                    return JobCard(
                      job: job,
                      onRetry: () => _retryJob(context, ref, job),
                      onViewDetail: () => showJobDetailSheet(context, job),
                    );
                  },
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _retryJob(
    BuildContext context,
    WidgetRef ref,
    Job job,
  ) async {
    try {
      final repo = ref.read(jobDashboardRepositoryProvider);
      final newJobId = await repo.retryJob(job.id);
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Job retried (new job: $newJobId)')),
        );
        ref.invalidate(exceptionsRowsProvider);
      }
    } on DioException catch (e) {
      if (context.mounted) {
        final message = e.response?.statusCode == 409
            ? 'Job is not retryable'
            : 'Retry failed: ${e.message}';
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(message)),
        );
      }
    }
  }
}

class _ExceptionsFilterChips extends ConsumerWidget {
  const _ExceptionsFilterChips({required this.selected});

  final ExceptionFilter selected;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context)!;
    final theme = Theme.of(context).extension<SummaTheme>()!;

    Widget chip(ExceptionFilter value, String label) {
      final isSelected = selected == value;
      return Padding(
        padding: const EdgeInsets.only(right: 8),
        child: ChoiceChip(
          label: Text(label),
          selected: isSelected,
          selectedColor: theme.accent.withOpacity(0.2),
          labelStyle: TextStyle(
            color: isSelected ? theme.accent : theme.textSecondary,
            fontSize: 12,
          ),
          onSelected: (_) {
            ref.read(exceptionsFilterProvider.notifier).state = value;
          },
        ),
      );
    }

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Row(
          children: [
            chip(ExceptionFilter.all, l10n.exceptionsFilterAll),
            chip(ExceptionFilter.failedExports,
                l10n.exceptionsFilterFailedExports),
            chip(ExceptionFilter.zombieJobs,
                l10n.exceptionsFilterZombieJobs),
          ],
        ),
      ),
    );
  }
}
