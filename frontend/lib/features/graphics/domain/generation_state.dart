/// Represents the full lifecycle of a graphic generation task.
enum GenerationPhase {
  idle,       // not started
  submitting, // POSTing to /generate
  polling,    // waiting for COMPLETED
  completed,  // image ready
  timeout,    // 60 polls exceeded
  failed,     // backend returned FAILED
}

class GenerationState {
  const GenerationState({
    this.phase = GenerationPhase.idle,
    this.taskId,
    this.resultUrl,
    this.pollAttempts = 0,
    this.errorMessage,
    this.errorCode,
  });

  final GenerationPhase phase;
  final String? taskId;
  final String? resultUrl;
  final int pollAttempts;
  final String? errorMessage;
  final String? errorCode;

  static const int maxPollAttempts = 60;

  GenerationState copyWith({
    GenerationPhase? phase,
    String? taskId,
    String? resultUrl,
    int? pollAttempts,
    String? errorMessage,
    String? errorCode,
  }) =>
      GenerationState(
        phase:        phase        ?? this.phase,
        taskId:       taskId       ?? this.taskId,
        resultUrl:    resultUrl    ?? this.resultUrl,
        pollAttempts: pollAttempts ?? this.pollAttempts,
        errorMessage: errorMessage ?? this.errorMessage,
        errorCode:    errorCode    ?? this.errorCode,
      );
}
