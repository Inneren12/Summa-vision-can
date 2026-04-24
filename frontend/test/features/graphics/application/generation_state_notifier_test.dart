import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:summa_vision_admin/features/graphics/application/generation_state_notifier.dart';
import 'package:summa_vision_admin/features/graphics/data/graphic_generation_repository.dart';
import 'package:summa_vision_admin/features/graphics/domain/graphics_generate_request.dart';
import 'package:summa_vision_admin/features/graphics/domain/job_status.dart';
import 'package:summa_vision_admin/features/graphics/domain/raw_data_upload.dart';

/// Fake repository implementing the public surface of
/// [GraphicGenerationRepository]. `_dio` is library-private so it is not part
/// of the interface contract from other libraries.
class _FakeGraphicGenerationRepository
    implements GraphicGenerationRepository {
  _FakeGraphicGenerationRepository({
    required this.submittedJobId,
    required this.statusSequence,
  });

  final String submittedJobId;
  final List<JobStatus> statusSequence;
  int _calls = 0;

  @override
  Future<String> submitGeneration(GraphicsGenerateRequest request) async =>
      submittedJobId;

  @override
  Future<String> submitGenerationFromData(
    GenerateFromDataRequest request,
  ) async =>
      submittedJobId;

  @override
  Future<JobStatus> getJobStatus(String jobId) async {
    final idx = _calls < statusSequence.length ? _calls : statusSequence.length - 1;
    _calls++;
    return statusSequence[idx];
  }
}

const _sampleRequest = GraphicsGenerateRequest(
  dataKey: 'statcan/processed/13-10-0888-01/data.parquet',
  chartType: 'line',
  title: 'Test Headline',
  size: [1080, 1080],
  category: 'housing',
);

void main() {
  group('ChartGenerationNotifier — error_code plumbing', () {
    test(
      'propagates backend error_code to state.errorCode on failed job',
      () async {
        final fakeRepo = _FakeGraphicGenerationRepository(
          submittedJobId: 'job-77',
          statusSequence: const [
            JobStatus(
              jobId: 'job-77',
              status: 'failed',
              errorCode: 'CHART_EMPTY_DF',
              errorMessage: 'raw backend text',
            ),
          ],
        );

        final container = ProviderContainer(
          overrides: [
            graphicGenerationRepositoryProvider.overrideWithValue(fakeRepo),
          ],
        );
        addTearDown(container.dispose);

        await container
            .read(chartGenerationNotifierProvider.notifier)
            .generate(_sampleRequest);

        final state = container.read(chartGenerationNotifierProvider);
        expect(state.phase, GenerationPhase.failed);
        expect(state.errorCode, 'CHART_EMPTY_DF');
        expect(state.errorMessage, 'raw backend text');
      },
      timeout: const Timeout(Duration(seconds: 20)),
    );

    test(
      'leaves state.errorCode null when backend omits error_code',
      () async {
        final fakeRepo = _FakeGraphicGenerationRepository(
          submittedJobId: 'job-78',
          statusSequence: const [
            JobStatus(
              jobId: 'job-78',
              status: 'failed',
              errorMessage: 'generic failure',
            ),
          ],
        );

        final container = ProviderContainer(
          overrides: [
            graphicGenerationRepositoryProvider.overrideWithValue(fakeRepo),
          ],
        );
        addTearDown(container.dispose);

        await container
            .read(chartGenerationNotifierProvider.notifier)
            .generate(_sampleRequest);

        final state = container.read(chartGenerationNotifierProvider);
        expect(state.phase, GenerationPhase.failed);
        expect(state.errorCode, isNull);
        expect(state.errorMessage, 'generic failure');
      },
      timeout: const Timeout(Duration(seconds: 20)),
    );
  });

  group('JobStatus.fromJson — error_code field', () {
    test('deserializes error_code from backend JSON', () {
      final status = JobStatus.fromJson({
        'job_id': 'job-1',
        'status': 'failed',
        'error_code': 'CHART_EMPTY_DF',
        'error_message': 'raw text',
      });

      expect(status.errorCode, 'CHART_EMPTY_DF');
      expect(status.errorMessage, 'raw text');
    });

    test('errorCode is null when key absent', () {
      final status = JobStatus.fromJson({
        'job_id': 'job-1',
        'status': 'failed',
        'error_message': 'oops',
      });

      expect(status.errorCode, isNull);
      expect(status.errorMessage, 'oops');
    });
  });
}
