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
      // Fresh construction — never reuse copyWith for terminal error states,
      // because copyWith(errorCode: null) is a no-op under `value ?? this.value`
      // semantics and would leak a stale code from a prior failed run.
      state = GenerationState(
        phase: GenerationPhase.failed,
        taskId: state.taskId,
        resultUrl: state.resultUrl,
        pollAttempts: state.pollAttempts,
        errorCode: null,
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
        // Fresh construction — see note in generate() catch branch.
        state = GenerationState(
          phase: GenerationPhase.failed,
          taskId: state.taskId,
          resultUrl: state.resultUrl,
          pollAttempts: state.pollAttempts,
          errorCode: status.errorCode,
          errorMessage: status.detail ?? 'Generation failed on server',
        );
        return;
      }
    }

    // 60 attempts exhausted — fresh construction so a stale errorCode from
    // a prior failed run cannot leak into the timeout presentation.
    state = GenerationState(
      phase: GenerationPhase.timeout,
      taskId: state.taskId,
      resultUrl: state.resultUrl,
      pollAttempts: state.pollAttempts,
      errorCode: null,
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
