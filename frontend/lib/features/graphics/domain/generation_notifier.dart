import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/graphic_repository.dart';
import 'generation_state.dart';
import 'task_status.dart';

/// Manages the full generation lifecycle: submit → poll → complete/timeout.
///
/// State is cached in Riverpod — navigating back and forth does NOT
/// restart generation if [phase] is already [GenerationPhase.completed].
class GenerationNotifier extends Notifier<GenerationState> {
  static const _pollInterval = Duration(seconds: 2);

  @override
  GenerationState build() => const GenerationState();

  /// Start generation for [briefId].
  /// If already completed, returns immediately (cache hit).
  Future<void> generate(int briefId) async {
    // Cache hit — don't re-trigger
    if (state.phase == GenerationPhase.completed) return;

    final repo = ref.read(graphicRepositoryProvider);

    try {
      // Phase 1: Submit
      state = state.copyWith(phase: GenerationPhase.submitting);
      final taskId = await repo.submitGeneration(briefId: briefId);
      state = state.copyWith(
        phase: GenerationPhase.polling,
        taskId: taskId,
        pollAttempts: 0,
      );

      // Phase 2: Poll
      await _poll(taskId, repo);
    } catch (e) {
      state = state.copyWith(
        phase: GenerationPhase.failed,
        errorMessage: e.toString(),
      );
    }
  }

  Future<void> _poll(String taskId, GraphicRepository repo) async {
    for (var attempt = 1; attempt <= GenerationState.maxPollAttempts; attempt++) {
      await Future.delayed(_pollInterval);

      final status = await repo.getTaskStatus(taskId);
      state = state.copyWith(pollAttempts: attempt);

      if (status.isCompleted && status.resultUrl != null) {
        state = state.copyWith(
          phase: GenerationPhase.completed,
          resultUrl: status.resultUrl,
        );
        return;
      }

      if (status.isFailed) {
        state = state.copyWith(
          phase: GenerationPhase.failed,
          errorCode: status.errorCode,
          errorMessage: status.detail ?? 'Generation failed on server',
        );
        return;
      }
    }

    // 60 attempts exhausted
    state = state.copyWith(
      phase: GenerationPhase.timeout,
      errorMessage: 'Generation timed out. Try again?',
    );
  }

  /// Reset state so the journalist can retry.
  void reset() => state = const GenerationState();
}

/// Family provider keyed by briefId so each brief has its own cached state.
final generationNotifierProvider = NotifierProvider<GenerationNotifier, GenerationState>(
  () => GenerationNotifier(),
);
