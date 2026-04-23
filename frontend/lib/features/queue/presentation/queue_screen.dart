import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:summa_vision_admin/l10n/generated/app_localizations.dart';

import '../../../core/routing/app_drawer.dart';
import '../../../core/theme/app_theme.dart';
import '../data/queue_repository.dart';
import '../domain/content_brief.dart';

class QueueScreen extends ConsumerWidget {
  const QueueScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context)!;
    final theme = Theme.of(context).extension<SummaTheme>()!;
    final queueAsync = ref.watch(queueProvider);

    return Scaffold(
      drawer: const AppDrawer(),
      appBar: AppBar(
        title: Text(l10n.queueTitle),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: l10n.queueRefreshTooltip,
            onPressed: () => ref.invalidate(queueProvider),
          ),
        ],
      ),
      body: queueAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (err, stack) => Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.error_outline, color: theme.destructive, size: 48),
              const SizedBox(height: 16),
              Text(
                l10n.queueLoadError(err.toString()),
                textAlign: TextAlign.center,
                style: TextStyle(color: theme.textSecondary),
              ),
              const SizedBox(height: 16),
              ElevatedButton(
                onPressed: () => ref.invalidate(queueProvider),
                child: Text(l10n.commonRetryVerb),
              ),
            ],
          ),
        ),
        data: (briefs) => briefs.isEmpty
            ? const _EmptyQueueView()
            : ListView.separated(
                padding: const EdgeInsets.all(16),
                itemCount: briefs.length,
                separatorBuilder: (_, __) => const SizedBox(height: 12),
                itemBuilder: (context, index) => _BriefCard(
                  brief: briefs[index],
                  onApprove: () => context.go(
                    '/editor/${briefs[index].id}',
                  ),
                  onReject: () {
                    ref.invalidate(queueProvider);
                  },
                ),
              ),
      ),
    );
  }
}

class _EmptyQueueView extends StatelessWidget {
  const _EmptyQueueView();

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final theme = Theme.of(context).extension<SummaTheme>()!;
    return Center(
      child: Text(
        l10n.queueEmptyState,
        textAlign: TextAlign.center,
        style: TextStyle(color: theme.textSecondary),
      ),
    );
  }
}

class _BriefCard extends StatelessWidget {
  const _BriefCard({
    required this.brief,
    required this.onApprove,
    required this.onReject,
  });

  final ContentBrief brief;
  final VoidCallback onApprove;
  final VoidCallback onReject;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final theme = Theme.of(context).extension<SummaTheme>()!;

    Color scoreColour(double score) {
      if (score > 8) return theme.dataPositive;
      if (score >= 7) return theme.dataWarning;
      return theme.destructive;
    }

    final viralityColor = scoreColour(brief.viralityScore);

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                // Virality score badge
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: viralityColor.withOpacity(0.15),
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(
                      color: viralityColor,
                      width: 1,
                    ),
                  ),
                  child: Text(
                    brief.viralityScore.toStringAsFixed(1),
                    style: TextStyle(
                      color: viralityColor,
                      fontWeight: FontWeight.bold,
                      fontSize: 13,
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                // Chart type chip
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: theme.bgSurface,
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: Text(
                    brief.chartType,
                    style: TextStyle(
                      color: theme.dataGov,
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            // Headline
            Text(
              brief.headline,
              style: TextStyle(
                color: theme.textPrimary,
                fontSize: 15,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 16),
            // Action buttons
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                OutlinedButton(
                  onPressed: onReject,
                  style: OutlinedButton.styleFrom(
                    foregroundColor: theme.destructive,
                    side: BorderSide(color: theme.destructive),
                  ),
                  child: Text(l10n.queueRejectVerb),
                ),
                const SizedBox(width: 12),
                ElevatedButton(
                  onPressed: onApprove,
                  child: Text(l10n.queueApproveVerb),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
