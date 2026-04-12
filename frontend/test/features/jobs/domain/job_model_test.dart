import 'package:flutter_test/flutter_test.dart';
import 'package:summa_vision_admin/features/jobs/domain/job.dart';

void main() {
  group('Job.fromJson', () {
    test('parses full JSON with all fields', () {
      final json = {
        'id': 'job-001',
        'job_type': 'graphics_generate',
        'status': 'success',
        'payload_json': '{"key":"value"}',
        'result_json': '{"publication_id":42}',
        'error_code': null,
        'error_message': null,
        'attempt_count': 1,
        'max_attempts': 3,
        'created_at': '2026-04-10T14:30:00Z',
        'started_at': '2026-04-10T14:30:01Z',
        'finished_at': '2026-04-10T14:30:25Z',
        'created_by': 'admin_api',
        'dedupe_key': 'graphics:13-10-0888-01:data:abc123',
      };

      final job = Job.fromJson(json);

      expect(job.id, 'job-001');
      expect(job.jobType, 'graphics_generate');
      expect(job.status, 'success');
      expect(job.payloadJson, '{"key":"value"}');
      expect(job.resultJson, '{"publication_id":42}');
      expect(job.errorCode, isNull);
      expect(job.errorMessage, isNull);
      expect(job.attemptCount, 1);
      expect(job.maxAttempts, 3);
      expect(job.createdAt, DateTime.utc(2026, 4, 10, 14, 30, 0));
      expect(job.startedAt, DateTime.utc(2026, 4, 10, 14, 30, 1));
      expect(job.finishedAt, DateTime.utc(2026, 4, 10, 14, 30, 25));
      expect(job.createdBy, 'admin_api');
      expect(job.dedupeKey, 'graphics:13-10-0888-01:data:abc123');
    });

    test('parses JSON with nullable fields as null', () {
      final json = {
        'id': 'job-002',
        'job_type': 'cube_fetch',
        'status': 'queued',
        'payload_json': null,
        'result_json': null,
        'error_code': null,
        'error_message': null,
        'attempt_count': 0,
        'max_attempts': 3,
        'created_at': '2026-04-10T14:30:00Z',
        'started_at': null,
        'finished_at': null,
        'created_by': null,
        'dedupe_key': null,
      };

      final job = Job.fromJson(json);

      expect(job.startedAt, isNull);
      expect(job.finishedAt, isNull);
      expect(job.createdBy, isNull);
      expect(job.dedupeKey, isNull);
    });
  });

  group('JobHelpers.isRetryable', () {
    test('failed + attempt_count < max_attempts → true', () {
      final job = Job(
        id: '1',
        jobType: 'graphics_generate',
        status: 'failed',
        attemptCount: 1,
        maxAttempts: 3,
        createdAt: DateTime.now(),
      );
      expect(job.isRetryable, isTrue);
    });

    test('success → false', () {
      final job = Job(
        id: '1',
        jobType: 'graphics_generate',
        status: 'success',
        attemptCount: 1,
        maxAttempts: 3,
        createdAt: DateTime.now(),
      );
      expect(job.isRetryable, isFalse);
    });

    test('failed + max attempts reached → false', () {
      final job = Job(
        id: '1',
        jobType: 'graphics_generate',
        status: 'failed',
        attemptCount: 3,
        maxAttempts: 3,
        createdAt: DateTime.now(),
      );
      expect(job.isRetryable, isFalse);
    });

    test('queued → false', () {
      final job = Job(
        id: '1',
        jobType: 'catalog_sync',
        status: 'queued',
        attemptCount: 0,
        maxAttempts: 3,
        createdAt: DateTime.now(),
      );
      expect(job.isRetryable, isFalse);
    });
  });

  group('JobHelpers.isStale', () {
    test('running + started 15 min ago → true', () {
      final job = Job(
        id: '1',
        jobType: 'cube_fetch',
        status: 'running',
        attemptCount: 1,
        maxAttempts: 3,
        createdAt: DateTime.now().subtract(const Duration(minutes: 20)),
        startedAt: DateTime.now().subtract(const Duration(minutes: 15)),
      );
      expect(job.isStale, isTrue);
    });

    test('running + started 2 min ago → false', () {
      final job = Job(
        id: '1',
        jobType: 'cube_fetch',
        status: 'running',
        attemptCount: 1,
        maxAttempts: 3,
        createdAt: DateTime.now().subtract(const Duration(minutes: 5)),
        startedAt: DateTime.now().subtract(const Duration(minutes: 2)),
      );
      expect(job.isStale, isFalse);
    });

    test('success + old started_at → false (not running)', () {
      final job = Job(
        id: '1',
        jobType: 'cube_fetch',
        status: 'success',
        attemptCount: 1,
        maxAttempts: 3,
        createdAt: DateTime.now().subtract(const Duration(hours: 1)),
        startedAt: DateTime.now().subtract(const Duration(hours: 1)),
        finishedAt: DateTime.now().subtract(const Duration(minutes: 59)),
      );
      expect(job.isStale, isFalse);
    });

    test('running + no startedAt → false', () {
      final job = Job(
        id: '1',
        jobType: 'cube_fetch',
        status: 'running',
        attemptCount: 1,
        maxAttempts: 3,
        createdAt: DateTime.now(),
      );
      expect(job.isStale, isFalse);
    });
  });

  group('JobHelpers.duration', () {
    test('started and finished → correct Duration', () {
      final start = DateTime.utc(2026, 4, 10, 14, 30, 0);
      final end = DateTime.utc(2026, 4, 10, 14, 30, 24);
      final job = Job(
        id: '1',
        jobType: 'graphics_generate',
        status: 'success',
        attemptCount: 1,
        maxAttempts: 3,
        createdAt: start,
        startedAt: start,
        finishedAt: end,
      );
      expect(job.duration, const Duration(seconds: 24));
    });

    test('still running (no finishedAt) → null', () {
      final job = Job(
        id: '1',
        jobType: 'graphics_generate',
        status: 'running',
        attemptCount: 1,
        maxAttempts: 3,
        createdAt: DateTime.now(),
        startedAt: DateTime.now(),
      );
      expect(job.duration, isNull);
    });

    test('not started (no startedAt) → null', () {
      final job = Job(
        id: '1',
        jobType: 'catalog_sync',
        status: 'queued',
        attemptCount: 0,
        maxAttempts: 3,
        createdAt: DateTime.now(),
      );
      expect(job.duration, isNull);
    });
  });

  group('JobHelpers.jobTypeDisplay', () {
    test('catalog_sync → Catalog Sync', () {
      final job = Job(
        id: '1',
        jobType: 'catalog_sync',
        status: 'queued',
        attemptCount: 0,
        maxAttempts: 3,
        createdAt: DateTime.now(),
      );
      expect(job.jobTypeDisplay, 'Catalog Sync');
    });

    test('cube_fetch → Data Fetch', () {
      final job = Job(
        id: '1',
        jobType: 'cube_fetch',
        status: 'queued',
        attemptCount: 0,
        maxAttempts: 3,
        createdAt: DateTime.now(),
      );
      expect(job.jobTypeDisplay, 'Data Fetch');
    });

    test('graphics_generate → Chart Generation', () {
      final job = Job(
        id: '1',
        jobType: 'graphics_generate',
        status: 'queued',
        attemptCount: 0,
        maxAttempts: 3,
        createdAt: DateTime.now(),
      );
      expect(job.jobTypeDisplay, 'Chart Generation');
    });

    test('unknown type → raw value', () {
      final job = Job(
        id: '1',
        jobType: 'some_new_type',
        status: 'queued',
        attemptCount: 0,
        maxAttempts: 3,
        createdAt: DateTime.now(),
      );
      expect(job.jobTypeDisplay, 'some_new_type');
    });
  });

  group('JobHelpers.statusDisplay', () {
    test('queued → Queued', () {
      final job = Job(
        id: '1',
        jobType: 'catalog_sync',
        status: 'queued',
        attemptCount: 0,
        maxAttempts: 3,
        createdAt: DateTime.now(),
      );
      expect(job.statusDisplay, 'Queued');
    });

    test('running → Running', () {
      final job = Job(
        id: '1',
        jobType: 'catalog_sync',
        status: 'running',
        attemptCount: 1,
        maxAttempts: 3,
        createdAt: DateTime.now(),
      );
      expect(job.statusDisplay, 'Running');
    });
  });
}
