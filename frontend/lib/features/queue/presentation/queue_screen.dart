import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_theme.dart';
import '../data/queue_repository.dart';
import '../domain/content_brief.dart';

class QueueScreen extends ConsumerWidget {
  const QueueScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final queueAsync = ref.watch(queueProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Brief Queue'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Refresh queue',
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
              const Icon(
                Icons.error_outline,
                color: AppTheme.errorRed,
                size: 48,
              ),
              const SizedBox(height: 16),
              Text(
                'Failed to load queue\n$err',
                textAlign: TextAlign.center,
                style: const TextStyle(color: AppTheme.textSecondary),
              ),
              const SizedBox(height: 16),
              ElevatedButton(
                onPressed: () => ref.invalidate(queueProvider),
                child: const Text('Retry'),
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
                  onApprove: () => context.go('/editor/${briefs[index].id}'),
                  onReject: () {
                    // Local optimistic removal — re-fetch on next refresh
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
    return const Center(
      child: Text(
        'No briefs in queue.\nTap refresh to fetch new ones.',
        textAlign: TextAlign.center,
        style: TextStyle(color: AppTheme.textSecondary),
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

  Color _scoreColour(double score) {
    if (score > 8) return AppTheme.neonGreen;
    if (score >= 7) return AppTheme.neonYellow;
    return AppTheme.neonPink;
  }

  @override
  Widget build(BuildContext context) {
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
                  padding: const EdgeInsets.symmetric(
                    horizontal: 8,
                    vertical: 4,
                  ),
                  decoration: BoxDecoration(
                    color: _scoreColour(brief.viralityScore).withOpacity(0.15),
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(
                      color: _scoreColour(brief.viralityScore),
                      width: 1,
                    ),
                  ),
                  child: Text(
                    brief.viralityScore.toStringAsFixed(1),
                    style: TextStyle(
                      color: _scoreColour(brief.viralityScore),
                      fontWeight: FontWeight.bold,
                      fontSize: 13,
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                // Chart type chip
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 8,
                    vertical: 4,
                  ),
                  decoration: BoxDecoration(
                    color: AppTheme.surfaceDark,
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: Text(
                    brief.chartType,
                    style: const TextStyle(
                      color: AppTheme.neonBlue,
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
              style: const TextStyle(
                color: AppTheme.textPrimary,
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
                    foregroundColor: AppTheme.neonPink,
                    side: const BorderSide(color: AppTheme.neonPink),
                  ),
                  child: const Text('Reject'),
                ),
                const SizedBox(width: 12),
                ElevatedButton(
                  onPressed: onApprove,
                  child: const Text('Approve'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
