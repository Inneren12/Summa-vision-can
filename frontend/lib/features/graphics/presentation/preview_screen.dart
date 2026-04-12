import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/theme/app_theme.dart';
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
    final state = ref.watch(generationNotifierProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Generating Graphic')),
      body: switch (state.phase) {
        GenerationPhase.idle ||
        GenerationPhase.submitting => const _SubmittingView(),
        GenerationPhase.polling => _PollingView(
          attempt: state.pollAttempts,
          max: GenerationState.maxPollAttempts,
        ),
        GenerationPhase.completed => _CompletedView(
          resultUrl: state.resultUrl!,
        ),
        GenerationPhase.timeout => _ErrorView(
          message: 'Generation timed out. Try again?',
          onRetry: () {
            ref.read(generationNotifierProvider.notifier).reset();
            final briefId = int.tryParse(widget.taskId) ?? 0;
            ref.read(generationNotifierProvider.notifier).generate(briefId);
          },
        ),
        GenerationPhase.failed => _ErrorView(
          message: state.errorMessage ?? 'Generation failed.',
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
  Widget build(BuildContext context) => const Center(
    child: Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        CircularProgressIndicator(),
        SizedBox(height: 16),
        Text(
          'Submitting generation task...',
          style: TextStyle(color: AppTheme.textSecondary),
        ),
      ],
    ),
  );
}

class _PollingView extends StatelessWidget {
  final int attempt;
  final int max;

  const _PollingView({required this.attempt, required this.max});

  @override
  Widget build(BuildContext context) => Center(
    child: Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        CircularProgressIndicator(
          value: attempt / max,
          color: AppTheme.neonGreen,
        ),
        const SizedBox(height: 16),
        Text(
          'Generating graphic... ($attempt/$max)',
          style: const TextStyle(color: AppTheme.textSecondary),
        ),
        const SizedBox(height: 8),
        const Text(
          'This may take up to 2 minutes.',
          style: TextStyle(color: AppTheme.textSecondary, fontSize: 12),
        ),
      ],
    ),
  );
}

class _CompletedView extends StatelessWidget {
  final String resultUrl;

  const _CompletedView({required this.resultUrl});

  @override
  Widget build(BuildContext context) => SingleChildScrollView(
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
            errorBuilder: (_, __, ___) => const Icon(
              Icons.broken_image,
              color: AppTheme.errorRed,
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
                ScaffoldMessenger.of(
                  context,
                ).showSnackBar(SnackBar(content: Text('Saved: $path')));
              }
            } catch (e) {
              if (context.mounted) {
                ScaffoldMessenger.of(
                  context,
                ).showSnackBar(SnackBar(content: Text('Download failed: $e')));
              }
            }
          },
          icon: const Icon(Icons.download),
          label: const Text('Download'),
        ),
      ],
    ),
  );
}

class _ErrorView extends StatelessWidget {
  final String message;
  final VoidCallback onRetry;

  const _ErrorView({required this.message, required this.onRetry});

  @override
  Widget build(BuildContext context) => Center(
    child: Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        const Icon(Icons.error_outline, color: AppTheme.errorRed, size: 48),
        const SizedBox(height: 16),
        Text(
          message,
          key: const Key('error_message'),
          textAlign: TextAlign.center,
          style: const TextStyle(color: AppTheme.textSecondary),
        ),
        const SizedBox(height: 24),
        ElevatedButton(
          key: const Key('retry_btn'),
          onPressed: onRetry,
          child: const Text('Retry'),
        ),
      ],
    ),
  );
}
