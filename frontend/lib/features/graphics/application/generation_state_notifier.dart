import 'dart:convert';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:freezed_annotation/freezed_annotation.dart';

import '../data/graphic_generation_repository.dart';
import '../domain/generation_result.dart';
import '../domain/graphics_generate_request.dart';

part 'generation_state_notifier.freezed.dart';

/// Phases of the C-3 async generation lifecycle.
enum GenerationPhase { idle, submitting, polling, success, failed, timeout }

@freezed
class ChartGenerationState with _$ChartGenerationState {
  const factory ChartGenerationState({
    @Default(GenerationPhase.idle) GenerationPhase phase,
    String? jobId,
    GenerationResult? result,
    String? errorMessage,
    @Default(0) int pollCount,
  }) = _ChartGenerationState;
}

/// Manages submit → poll → result for C-3 chart generation.
///
/// State is cached in Riverpod — navigating away and back does NOT
/// restart generation if [phase] is already [GenerationPhase.success].
class ChartGenerationNotifier extends Notifier<ChartGenerationState> {
  static const _pollInterval = Duration(seconds: 2);
  static const int maxPolls = 60;

  @override
  ChartGenerationState build() => const ChartGenerationState();

  /// Kick off a generation job. No-op if already succeeded (cache hit).
  Future<void> generate(GraphicsGenerateRequest request) async {
    if (state.phase == GenerationPhase.success) return;

    final repo = ref.read(graphicGenerationRepositoryProvider);

    try {
      // Phase 1: Submit
      state = state.copyWith(phase: GenerationPhase.submitting);
      final jobId = await repo.submitGeneration(request);
      state = state.copyWith(
        phase: GenerationPhase.polling,
        jobId: jobId,
        pollCount: 0,
      );

      // Phase 2: Poll
      await _poll(jobId, repo);
    } catch (e) {
      state = state.copyWith(
        phase: GenerationPhase.failed,
        errorMessage: e.toString(),
      );
    }
  }

  Future<void> _poll(
    String jobId,
    GraphicGenerationRepository repo,
  ) async {
    for (var attempt = 1; attempt <= maxPolls; attempt++) {
      await Future.delayed(_pollInterval);

      final jobStatus = await repo.getJobStatus(jobId);
      state = state.copyWith(pollCount: attempt);

      if (jobStatus.isSuccess && jobStatus.resultJson != null) {
        final resultMap =
            jsonDecode(jobStatus.resultJson!) as Map<String, dynamic>;
        final result = GenerationResult.fromJson(resultMap);
        state = state.copyWith(
          phase: GenerationPhase.success,
          result: result,
        );
        return;
      }

      if (jobStatus.isFailed) {
        state = state.copyWith(
          phase: GenerationPhase.failed,
          errorMessage:
              jobStatus.errorMessage ?? 'Generation failed on server',
        );
        return;
      }
    }

    // 60 polls exhausted
    state = state.copyWith(
      phase: GenerationPhase.timeout,
      errorMessage: 'Generation timed out after 2 minutes.',
    );
  }

  /// Reset to idle so the operator can reconfigure and retry.
  void reset() => state = const ChartGenerationState();
}

final chartGenerationNotifierProvider =
    NotifierProvider<ChartGenerationNotifier, ChartGenerationState>(
  () => ChartGenerationNotifier(),
);
