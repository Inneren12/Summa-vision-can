import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/theme/app_theme.dart';
import '../../../l10n/backend_errors.dart';
import '../../../l10n/generated/app_localizations.dart';
import '../data/download_helper.dart';
import '../domain/generation_notifier.dart';
import '../domain/generation_state.dart';

class PreviewScreen extends ConsumerStatefulWidget {
  final String taskId; // actually briefId passed from EditorScreen

  const PreviewScreen({super.key, required this.taskId});

  @override
  ConsumerState<PreviewScreen> createState() => _PreviewScreenState();
}

class _PreviewScreenState extends ConsumerState<PreviewScreen> {
  @override
  void initState() {
    super.initState();
    // Trigger generation after first frame
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final briefId = int.tryParse(widget.taskId) ?? 0;
      ref.read(generationNotifierProvider.notifier).generate(briefId);
    });
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context).extension<SummaTheme>()!;
    final l10n = AppLocalizations.of(context)!;
    final state = ref.watch(generationNotifierProvider);

    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.previewAppBarTitle),
      ),
      body: switch (state.phase) {
        GenerationPhase.idle => Center(
          child: Text(
            l10n.generationStatusSubmitting,
            style: TextStyle(color: theme.textSecondary),
          ),
        ),
        GenerationPhase.submitting => const _SubmittingView(),
        GenerationPhase.polling => _PollingView(
            attempt: state.pollAttempts,
            max: GenerationState.maxPollAttempts,
          ),
        GenerationPhase.completed => _CompletedView(
            resultUrl: state.resultUrl!,
          ),
        GenerationPhase.timeout => _ErrorView(
            message: l10n.generationStatusTimeout,
            onRetry: () {
              ref.read(generationNotifierProvider.notifier).reset();
              final briefId = int.tryParse(widget.taskId) ?? 0;
              ref.read(generationNotifierProvider.notifier).generate(briefId);
            },
          ),
        GenerationPhase.failed => _ErrorView(
            message: mapBackendErrorCode(state.errorCode, l10n) ??
                state.errorMessage ??
                l10n.generationStatusFailed,
            onRetry: () {
              ref.read(generationNotifierProvider.notifier).reset();
              final briefId = int.tryParse(widget.taskId) ?? 0;
              ref.read(generationNotifierProvider.notifier).generate(briefId);
            },
          ),
      },
    );
  }
}

class _SubmittingView extends StatelessWidget {
  const _SubmittingView();

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context).extension<SummaTheme>()!;
    final l10n = AppLocalizations.of(context)!;
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const CircularProgressIndicator(),
          const SizedBox(height: 16),
          Text(
            l10n.generationStatusSubmitting,
            style: TextStyle(color: theme.textSecondary),
          ),
        ],
      ),
    );
  }
}

class _PollingView extends StatelessWidget {
  final int attempt;
  final int max;

  const _PollingView({required this.attempt, required this.max});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context).extension<SummaTheme>()!;
    final l10n = AppLocalizations.of(context)!;
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          CircularProgressIndicator(
            value: attempt / max,
            color: theme.accent,
          ),
          const SizedBox(height: 16),
          Text(
            l10n.generationStatusPolling(attempt, max),
            style: TextStyle(color: theme.textSecondary),
          ),
          const SizedBox(height: 8),
          Text(
            l10n.previewEtaText,
            style: TextStyle(
              color: theme.textSecondary,
              fontSize: 12,
            ),
          ),
        ],
      ),
    );
  }
}

class _CompletedView extends StatelessWidget {
  final String resultUrl;

  const _CompletedView({required this.resultUrl});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context).extension<SummaTheme>()!;
    final l10n = AppLocalizations.of(context)!;
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        children: [
          ClipRRect(
            borderRadius: BorderRadius.circular(12),
            child: Image.network(
              resultUrl,
              fit: BoxFit.contain,
              loadingBuilder: (_, child, progress) {
                if (progress == null) return child;
                return const SizedBox(
                  height: 200,
                  child: Center(child: CircularProgressIndicator()),
                );
              },
              errorBuilder: (_, __, ___) => Icon(
                Icons.broken_image,
                color: theme.destructive,
                size: 64,
              ),
            ),
          ),
          const SizedBox(height: 24),
          ElevatedButton.icon(
            key: const Key('download_btn'),
            onPressed: () async {
              try {
                final path = await downloadAndSaveImage(resultUrl);
                if (context.mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(content: Text(l10n.previewDownloadSaved(path))),
                  );
                }
              } catch (e) {
                if (context.mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(
                      content: Text(l10n.previewDownloadFailed(e.toString())),
                    ),
                  );
                }
              }
            },
            icon: const Icon(Icons.download),
            label: Text(l10n.previewDownloadButton),
          ),
        ],
      ),
    );
  }
}

class _ErrorView extends StatelessWidget {
  final String message;
  final VoidCallback onRetry;

  const _ErrorView({required this.message, required this.onRetry});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context).extension<SummaTheme>()!;
    final l10n = AppLocalizations.of(context)!;
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.error_outline, color: theme.destructive, size: 48),
          const SizedBox(height: 16),
          Text(
            message,
            key: const Key('error_message'),
            textAlign: TextAlign.center,
            style: TextStyle(color: theme.textSecondary),
          ),
          const SizedBox(height: 24),
          ElevatedButton(
            key: const Key('retry_btn'),
            onPressed: onRetry,
            child: Text(l10n.commonRetryVerb),
          ),
        ],
      ),
    );
  }
}
