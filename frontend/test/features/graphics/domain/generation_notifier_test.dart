import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:summa_vision_admin/features/graphics/data/graphic_repository.dart';
import 'package:summa_vision_admin/features/graphics/domain/generation_notifier.dart';
import 'package:summa_vision_admin/features/graphics/domain/generation_state.dart';
import 'package:summa_vision_admin/features/graphics/domain/task_status.dart';

/// Fake repository that scripts submit + status responses.
///
/// Implements the public surface of [GraphicRepository]. `_dio` is
/// library-private so it is NOT part of the interface contract from other
/// libraries; no stub is required here.
class _FakeGraphicRepository implements GraphicRepository {
  _FakeGraphicRepository({
    required this.submittedTaskId,
    required this.statusSequence,
  });

  final String submittedTaskId;
  final List<TaskStatus> statusSequence;
  int _calls = 0;

  @override
  Future<String> submitGeneration({
    required int briefId,
    String sizePreset = 'twitter',
    int dpi = 150,
    bool watermark = true,
  }) async =>
      submittedTaskId;

  @override
  Future<TaskStatus> getTaskStatus(String taskId) async {
    final idx = _calls < statusSequence.length ? _calls : statusSequence.length - 1;
    _calls++;
    return statusSequence[idx];
  }
}

void main() {
  group('GenerationNotifier — error_code plumbing', () {
    test(
      'propagates backend error_code to state.errorCode on failed job',
      () async {
        final fakeRepo = _FakeGraphicRepository(
          submittedTaskId: 'task-42',
          statusSequence: const [
            TaskStatus(
              taskId: 'task-42',
              status: 'FAILED',
              errorCode: 'CHART_EMPTY_DF',
              detail: 'raw backend text',
            ),
          ],
        );

        final container = ProviderContainer(
          overrides: [
            graphicRepositoryProvider.overrideWithValue(fakeRepo),
          ],
        );
        addTearDown(container.dispose);

        await container.read(generationNotifierProvider.notifier).generate(42);

        final state = container.read(generationNotifierProvider);
        expect(state.phase, GenerationPhase.failed);
        expect(state.errorCode, 'CHART_EMPTY_DF');
        expect(state.errorMessage, 'raw backend text');
      },
      timeout: const Timeout(Duration(seconds: 20)),
    );

    test(
      'leaves state.errorCode null when backend omits error_code',
      () async {
        final fakeRepo = _FakeGraphicRepository(
          submittedTaskId: 'task-99',
          statusSequence: const [
            TaskStatus(
              taskId: 'task-99',
              status: 'FAILED',
              detail: 'generic failure',
            ),
          ],
        );

        final container = ProviderContainer(
          overrides: [
            graphicRepositoryProvider.overrideWithValue(fakeRepo),
          ],
        );
        addTearDown(container.dispose);

        await container.read(generationNotifierProvider.notifier).generate(99);

        final state = container.read(generationNotifierProvider);
        expect(state.phase, GenerationPhase.failed);
        expect(state.errorCode, isNull);
        expect(state.errorMessage, 'generic failure');
      },
      timeout: const Timeout(Duration(seconds: 20)),
    );
  });

  group('TaskStatus.fromJson — error_code field', () {
    test('deserializes error_code from backend JSON', () {
      final status = TaskStatus.fromJson({
        'task_id': 'task-1',
        'status': 'FAILED',
        'error_code': 'CHART_INSUFFICIENT_COLUMNS',
        'detail': 'raw message',
      });

      expect(status.errorCode, 'CHART_INSUFFICIENT_COLUMNS');
      expect(status.detail, 'raw message');
    });
  });
}
