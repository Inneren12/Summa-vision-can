import 'package:flutter_test/flutter_test.dart';
import 'package:summa_vision_admin/features/jobs/domain/job.dart';

void main() {
  group('Job Model Tests', () {
    test('test_job_from_json parses full JSON correctly', () {
      final json = {
        "id": "123",
        "job_type": "graphics_generate",
        "status": "success",
        "payload_json": "{\"data_key\":\"statcan\"}",
        "result_json": "{\"publication_id\":42}",
        "error_code": null,
        "error_message": null,
        "attempt_count": 1,
        "max_attempts": 3,
        "created_at": "2026-04-10T14:30:00.000Z",
        "started_at": "2026-04-10T14:30:01.000Z",
        "finished_at": "2026-04-10T14:30:25.000Z",
        "created_by": "admin_api",
        "dedupe_key": "graphics:123"
      };

      final job = Job.fromJson(json);

      expect(job.id, "123");
      expect(job.jobType, "graphics_generate");
      expect(job.status, "success");
      expect(job.payloadJson, "{\"data_key\":\"statcan\"}");
      expect(job.resultJson, "{\"publication_id\":42}");
      expect(job.attemptCount, 1);
      expect(job.createdAt, DateTime.utc(2026, 4, 10, 14, 30));
    });

    test('test_job_is_retryable', () {
      final jobRetryable = Job(
        id: "1", jobType: "test", status: "failed", attemptCount: 1, maxAttempts: 3, createdAt: DateTime.now(),
      );
      expect(jobRetryable.isRetryable, isTrue);

      final jobSuccess = jobRetryable.copyWith(status: "success");
      expect(jobSuccess.isRetryable, isFalse);

      final jobExhausted = jobRetryable.copyWith(attemptCount: 3);
      expect(jobExhausted.isRetryable, isFalse);
    });

    test('test_job_is_stale', () {
      final now = DateTime.now();

      final staleJob = Job(
        id: "1", jobType: "test", status: "running", attemptCount: 1, maxAttempts: 3,
        createdAt: now.subtract(const Duration(minutes: 20)),
        startedAt: now.subtract(const Duration(minutes: 15)),
      );
      expect(staleJob.isStale, isTrue);

      final freshJob = staleJob.copyWith(startedAt: now.subtract(const Duration(minutes: 2)));
      expect(freshJob.isStale, isFalse);

      final oldSuccessJob = staleJob.copyWith(status: "success");
      expect(oldSuccessJob.isStale, isFalse);
    });

    test('test_job_duration', () {
      final now = DateTime.now();
      final startedAt = now.subtract(const Duration(minutes: 5));
      final finishedAt = now;

      final jobWithDuration = Job(
        id: "1", jobType: "test", status: "success", attemptCount: 1, maxAttempts: 3,
        createdAt: startedAt.subtract(const Duration(seconds: 5)),
        startedAt: startedAt,
        finishedAt: finishedAt,
      );
      expect(jobWithDuration.duration?.inMinutes, 5);

      final runningJob = jobWithDuration.copyWith(finishedAt: null);
      expect(runningJob.duration, isNull);
    });

    test('test_job_type_display', () {
      final catalog = Job(id: "1", jobType: "catalog_sync", status: "queued", attemptCount: 0, maxAttempts: 3, createdAt: DateTime.now());
      expect(catalog.jobTypeDisplay, 'Catalog Sync');

      final fetch = catalog.copyWith(jobType: "cube_fetch");
      expect(fetch.jobTypeDisplay, 'Data Fetch');

      final unknown = catalog.copyWith(jobType: "unknown_type");
      expect(unknown.jobTypeDisplay, 'unknown_type');
    });
  });
}
