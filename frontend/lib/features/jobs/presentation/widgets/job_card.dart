import 'dart:async';

import 'package:flutter/material.dart';

import '../../../../core/theme/app_theme.dart';
import '../../domain/job.dart';

/// Card widget displaying a single job's summary info.
class JobCard extends StatelessWidget {
  const JobCard({
    super.key,
    required this.job,
    required this.onRetry,
    required this.onViewDetail,
  });

  final Job job;
  final VoidCallback onRetry;
  final VoidCallback onViewDetail;

  Color _statusColor(String status, SummaTheme theme) {
    switch (status) {
      case 'queued':
        return theme.textMuted;
      case 'running':
        return theme.dataGov;
      case 'success':
        return theme.dataPositive;
      case 'failed':
        return theme.destructive;
      case 'cancelled':
        return theme.textSecondary;
      default:
        return theme.textSecondary;
    }
  }

  String _formatDuration(Duration d) {
    final minutes = d.inMinutes;
    final seconds = d.inSeconds % 60;
    if (minutes > 0) return '${minutes}m ${seconds}s';
    return '${seconds}s';
  }

  String _formatDateTime(DateTime dt) {
    return '${dt.year}-${dt.month.toString().padLeft(2, '0')}-'
        '${dt.day.toString().padLeft(2, '0')} '
        '${dt.hour.toString().padLeft(2, '0')}:'
        '${dt.minute.toString().padLeft(2, '0')}';
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context).extension<SummaTheme>()!;
    final statusColor = _statusColor(job.status, theme);
    final isStale = job.isStale;
    final duration = job.duration;
    final isRetryable = job.isRetryable;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Row 1: Status badge, job type, duration
            Row(
              children: [
                _StatusBadge(
                  status: job.statusDisplay,
                  color: statusColor,
                  isRunning: job.status == 'running',
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    job.jobTypeDisplay,
                    style: TextStyle(
                      color: theme.textPrimary,
                      fontSize: 15,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
                if (duration != null)
                  Text(
                    _formatDuration(duration),
                    style: TextStyle(
                      color: theme.textSecondary,
                      fontSize: 13,
                      fontFamily: 'monospace',
                    ),
                  ),
                if (job.status == 'running' && job.startedAt != null)
                  _ElapsedTimer(startedAt: job.startedAt!),
              ],
            ),
            const SizedBox(height: 12),

            // Row 2: Created at + created by
            Text(
              'Created: ${_formatDateTime(job.createdAt)}'
              '${job.createdBy != null ? ' by ${job.createdBy}' : ''}',
              style: TextStyle(
                color: theme.textSecondary,
                fontSize: 13,
              ),
            ),
            const SizedBox(height: 4),

            // Row 3: Attempts
            Row(
              children: [
                Text(
                  'Attempts: ${job.attemptCount}/${job.maxAttempts}',
                  style: TextStyle(
                    color: job.attemptCount > 1
                        ? theme.dataWarning
                        : theme.textSecondary,
                    fontSize: 13,
                    fontWeight: job.attemptCount > 1
                        ? FontWeight.w600
                        : FontWeight.normal,
                  ),
                ),
              ],
            ),

            // Row 4: Dedupe key (if present)
            if (job.dedupeKey != null) ...[
              const SizedBox(height: 4),
              Tooltip(
                message: job.dedupeKey!,
                child: Text(
                  'Dedupe: ${job.dedupeKey!.length > 40 ? '${job.dedupeKey!.substring(0, 40)}...' : job.dedupeKey!}',
                  style: TextStyle(
                    color: theme.textSecondary,
                    fontSize: 12,
                    fontFamily: 'monospace',
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],

            // Stale warning
            if (isStale) ...[
              const SizedBox(height: 8),
              Container(
                width: double.infinity,
                padding:
                    const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                decoration: BoxDecoration(
                  color: theme.dataWarning.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(
                    color: theme.dataWarning.withOpacity(0.4),
                  ),
                ),
                child: Row(
                  children: [
                    Icon(Icons.warning_amber,
                        color: theme.dataWarning, size: 18),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        'Running for ${DateTime.now().difference(job.startedAt!).inMinutes} minutes \u2014 may be stale',
                        style: TextStyle(
                          color: theme.dataWarning,
                          fontSize: 13,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],

            // Error info for failed jobs
            if (job.status == 'failed' &&
                (job.errorCode != null || job.errorMessage != null)) ...[
              const SizedBox(height: 8),
              Container(
                width: double.infinity,
                padding:
                    const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                decoration: BoxDecoration(
                  color: theme.destructive.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(
                    color: theme.destructive.withOpacity(0.4),
                  ),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    if (job.errorCode != null)
                      Text(
                        job.errorCode!,
                        style: TextStyle(
                          color: theme.destructive,
                          fontSize: 13,
                          fontWeight: FontWeight.w600,
                          fontFamily: 'monospace',
                        ),
                      ),
                    if (job.errorMessage != null) ...[
                      if (job.errorCode != null) const SizedBox(height: 4),
                      Text(
                        job.errorMessage!.length > 120
                            ? '${job.errorMessage!.substring(0, 120)}...'
                            : job.errorMessage!,
                        style: TextStyle(
                          color: theme.destructive.withOpacity(0.85),
                          fontSize: 12,
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ],

            const SizedBox(height: 12),

            // Action buttons
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                if (isRetryable)
                  OutlinedButton.icon(
                    onPressed: onRetry,
                    icon: const Icon(Icons.replay, size: 16),
                    label: const Text('Retry'),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: theme.dataWarning,
                      side: BorderSide(color: theme.dataWarning),
                    ),
                  ),
                if (isRetryable) const SizedBox(width: 12),
                OutlinedButton(
                  onPressed: onViewDetail,
                  style: OutlinedButton.styleFrom(
                    foregroundColor: theme.dataGov,
                    side: BorderSide(color: theme.dataGov),
                  ),
                  child: const Text('View Detail'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

/// Colored chip showing job status.
class _StatusBadge extends StatelessWidget {
  const _StatusBadge({
    required this.status,
    required this.color,
    this.isRunning = false,
  });

  final String status;
  final Color color;
  final bool isRunning;

  @override
  Widget build(BuildContext context) {
    final badge = Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withOpacity(0.15),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: color, width: 1),
      ),
      child: Text(
        status,
        style: TextStyle(
          color: color,
          fontWeight: FontWeight.bold,
          fontSize: 12,
        ),
      ),
    );

    if (!isRunning) return badge;

    // Pulsing animation for running status
    return _PulsingWidget(child: badge);
  }
}

/// Wraps a child in a subtle pulsing animation.
class _PulsingWidget extends StatefulWidget {
  const _PulsingWidget({required this.child});
  final Widget child;

  @override
  State<_PulsingWidget> createState() => _PulsingWidgetState();
}

class _PulsingWidgetState extends State<_PulsingWidget>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  late final Animation<double> _animation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    )..repeat(reverse: true);
    _animation = Tween<double>(begin: 0.6, end: 1.0).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeInOut),
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _animation,
      builder: (context, child) =>
          Opacity(opacity: _animation.value, child: child),
      child: widget.child,
    );
  }
}

/// Live elapsed-time counter for running jobs.
class _ElapsedTimer extends StatefulWidget {
  const _ElapsedTimer({required this.startedAt});
  final DateTime startedAt;

  @override
  State<_ElapsedTimer> createState() => _ElapsedTimerState();
}

class _ElapsedTimerState extends State<_ElapsedTimer> {
  late final Timer _timer;
  Duration _elapsed = Duration.zero;

  @override
  void initState() {
    super.initState();
    _elapsed = DateTime.now().difference(widget.startedAt);
    _timer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (mounted) {
        setState(() {
          _elapsed = DateTime.now().difference(widget.startedAt);
        });
      }
    });
  }

  @override
  void dispose() {
    _timer.cancel();
    super.dispose();
  }

  String _format(Duration d) {
    final minutes = d.inMinutes;
    final seconds = d.inSeconds % 60;
    if (minutes > 0) return '${minutes}m ${seconds}s';
    return '${seconds}s';
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context).extension<SummaTheme>()!;
    return Text(
      _format(_elapsed),
      style: TextStyle(
        color: theme.dataGov,
        fontSize: 13,
        fontFamily: 'monospace',
      ),
    );
  }
}
