import 'dart:convert';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:freezed_annotation/freezed_annotation.dart';

import '../data/graphic_generation_repository.dart';
import '../domain/generation_result.dart';
import '../domain/graphics_generate_request.dart';
import '../domain/raw_data_upload.dart';

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
    String? errorCode,
    @Default(0) int pollCount,
  }) = _ChartGenerationState;
}

/// Manages submit → poll → result for C-3 chart generation.
///
/// State is reset when the operator navigates to a different dataset.
/// Re-generation is only blocked while a job is actively submitting or polling.
class ChartGenerationNotifier extends Notifier<ChartGenerationState> {
  static const _pollInterval = Duration(seconds: 2);
  static const int maxPolls = 60;

  @override
  ChartGenerationState build() => const ChartGenerationState();

  /// Kick off a generation job. No-op if already submitting or polling.
  Future<void> generate(GraphicsGenerateRequest request) async {
    if (state.phase == GenerationPhase.submitting ||
        state.phase == GenerationPhase.polling) return;

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

      if (jobStatus.status == 'success' && jobStatus.resultJson != null) {
        final resultMap =
            jsonDecode(jobStatus.resultJson!) as Map<String, dynamic>;
        final result = GenerationResult.fromJson(resultMap);
        state = state.copyWith(
          phase: GenerationPhase.success,
          result: result,
        );
        return;
      }

      if (jobStatus.status == 'failed') {
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

  /// Kick off a generation job from user-uploaded JSON/CSV data.
  ///
  /// No-op if a submission is already in flight. Shares submit → poll →
  /// result phases with [generate] so the UI can continue to branch on
  /// ``GenerationPhase`` without any upload-specific additions.
  Future<void> generateFromData(GenerateFromDataRequest request) async {
    if (state.phase == GenerationPhase.submitting ||
        state.phase == GenerationPhase.polling) return;

    final repo = ref.read(graphicGenerationRepositoryProvider);

    try {
      state = state.copyWith(phase: GenerationPhase.submitting);
      final jobId = await repo.submitGenerationFromData(request);
      state = state.copyWith(
        phase: GenerationPhase.polling,
        jobId: jobId,
        pollCount: 0,
      );
      await _poll(jobId, repo);
    } catch (e) {
      state = state.copyWith(
        phase: GenerationPhase.failed,
        errorMessage: e.toString(),
      );
    }
  }

  /// Reset to idle so the operator can reconfigure and retry.
  void reset() => state = const ChartGenerationState();
}

final chartGenerationNotifierProvider =
    NotifierProvider<ChartGenerationNotifier, ChartGenerationState>(
  () => ChartGenerationNotifier(),
);
