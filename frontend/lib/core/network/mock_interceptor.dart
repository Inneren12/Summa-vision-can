import 'package:dio/dio.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';

/// Returns local JSON fixtures instead of hitting the real backend.
///
/// Enabled when [USE_MOCK=true] in the .env file.
///
/// IMPORTANT: Simulates realistic network delay via [Future.delayed]
/// so that [AsyncValue.loading] states are visible during development.
/// Without this delay, loading UI states flash for milliseconds and
/// loading-related bugs are invisible.
class MockInterceptor extends Interceptor {
  static const Duration _delay = Duration(seconds: 1);

  /// Allows tests to disable the artificial delay.
  final bool enableDelay;

  MockInterceptor({this.enableDelay = true});

  static bool get isEnabled => dotenv.env['USE_MOCK']?.toLowerCase() == 'true';

  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) {
    _handleRequest(options, handler);
  }

  Future<void> _handleRequest(
    RequestOptions options,
    RequestInterceptorHandler handler,
  ) async {
    if (enableDelay) {
      await Future.delayed(_delay);
    }

    final path = options.path;

    if (path.contains('/admin/queue')) {
      handler.resolve(
        Response(requestOptions: options, statusCode: 200, data: _queueFixture),
        true,
      );
      return;
    }

    if (path.contains('/admin/graphics/generate')) {
      handler.resolve(
        Response(
          requestOptions: options,
          statusCode: 202,
          data: {
            'task_id': 'mock-task-uuid-1234',
            'message': 'Generation started',
          },
        ),
        true,
      );
      return;
    }

    if (path.contains('/admin/tasks/')) {
      handler.resolve(
        Response(
          requestOptions: options,
          statusCode: 200,
          data: {
            'task_id': 'mock-task-uuid-1234',
            'status': 'COMPLETED',
            'result_url': 'https://placehold.co/1200x628.png',
          },
        ),
        true,
      );
      return;
    }

    if (path.endsWith('/retry')) {
      handler.resolve(
        Response(
          requestOptions: options,
          statusCode: 202,
          data: {"job_id": "mock-retry-job-001", "status": "queued"},
        ),
        true,
      );
      return;
    }

    if (path.contains('/admin/jobs')) {
      // Check if it's a specific job ID
      final RegExp exp = RegExp(r'/admin/jobs/([^/]+)$');
      final match = exp.firstMatch(path);
      if (match != null) {
        final id = match.group(1);
        final job = _jobsFixture.firstWhere(
          (j) => j['id'] == id,
          orElse: () => _jobsFixture.first,
        );
        handler.resolve(
          Response(requestOptions: options, statusCode: 200, data: job),
          true,
        );
        return;
      }

      // Filter by query params if present
      final jobType = options.queryParameters['job_type'];
      final status = options.queryParameters['status'];
      final limit = options.queryParameters['limit'] ?? 50;

      List<Map<String, dynamic>> filteredJobs = _jobsFixture;
      if (jobType != null) {
        filteredJobs = filteredJobs
            .where((j) => j['job_type'] == jobType)
            .toList();
      }
      if (status != null) {
        filteredJobs = filteredJobs
            .where((j) => j['status'] == status)
            .toList();
      }

      handler.resolve(
        Response(
          requestOptions: options,
          statusCode: 200,
          data: {
            'items': filteredJobs.take(limit as int).toList(),
            'total': filteredJobs.length,
          },
        ),
        true,
      );
      return;
    }

    // Pass through any unmatched routes
    handler.next(options);
  }

  static const List<Map<String, dynamic>> _queueFixture = [
    {
      'id': 1,
      'headline': 'Canadian housing prices surge 12% in Q4 2025',
      'chart_type': 'BAR',
      'virality_score': 9.1,
      'status': 'DRAFT',
      'created_at': '2026-03-17T10:00:00Z',
    },
    {
      'id': 2,
      'headline': 'CPI hits record high — grocery inflation at 8.3%',
      'chart_type': 'LINE',
      'virality_score': 8.7,
      'status': 'DRAFT',
      'created_at': '2026-03-17T09:30:00Z',
    },
    {
      'id': 3,
      'headline':
          'Bank of Canada holds rates steady for 3rd consecutive meeting',
      'chart_type': 'AREA',
      'virality_score': 7.2,
      'status': 'DRAFT',
      'created_at': '2026-03-17T09:00:00Z',
    },
  ];

  static final List<Map<String, dynamic>> _jobsFixture = [
    {
      "id": "mock-job-1",
      "job_type": "catalog_sync",
      "status": "queued",
      "payload_json": "{}",
      "result_json": null,
      "error_code": null,
      "error_message": null,
      "attempt_count": 0,
      "max_attempts": 3,
      "created_at": "2026-04-10T14:00:00Z",
      "started_at": null,
      "finished_at": null,
      "created_by": "system",
      "dedupe_key": "catalog_sync:2026-04-10",
    },
    {
      "id": "mock-job-2",
      "job_type": "cube_fetch",
      "status": "queued",
      "payload_json": "{\"product_id\": \"14-10-0127-01\"}",
      "result_json": null,
      "error_code": null,
      "error_message": null,
      "attempt_count": 0,
      "max_attempts": 3,
      "created_at": "2026-04-10T14:10:00Z",
      "started_at": null,
      "finished_at": null,
      "created_by": "operator",
      "dedupe_key": "cube_fetch:14-10-0127-01",
    },
    {
      "id": "mock-job-3",
      "job_type": "graphics_generate",
      "status": "running",
      "payload_json": "{\"data_key\":\"...\",\"chart_type\":\"line\"}",
      "result_json": null,
      "error_code": null,
      "error_message": null,
      "attempt_count": 1,
      "max_attempts": 3,
      "created_at": "2026-04-10T14:28:00Z",
      "started_at": DateTime.now()
          .subtract(const Duration(minutes: 2))
          .toIso8601String(),
      "finished_at": null,
      "created_by": "admin_api",
      "dedupe_key": "graphics_generate:...",
    },
    {
      "id": "mock-job-4",
      "job_type": "cube_fetch",
      "status": "running",
      "payload_json": "{\"product_id\": \"14-10-0287-01\"}",
      "result_json": null,
      "error_code": null,
      "error_message": null,
      "attempt_count": 1,
      "max_attempts": 3,
      "created_at": "2026-04-10T14:00:00Z",
      "started_at": DateTime.now()
          .subtract(const Duration(minutes: 15))
          .toIso8601String(),
      "finished_at": null,
      "created_by": "admin_api",
      "dedupe_key": "cube_fetch:14-10-0287-01",
    },
    {
      "id": "mock-job-5",
      "job_type": "graphics_generate",
      "status": "success",
      "payload_json": "{\"data_key\":\"...\",\"chart_type\":\"bar\"}",
      "result_json":
          "{\"publication_id\":42,\"cdn_url_lowres\":\"...\",\"version\":1}",
      "error_code": null,
      "error_message": null,
      "attempt_count": 1,
      "max_attempts": 3,
      "created_at": "2026-04-10T13:00:00Z",
      "started_at": "2026-04-10T13:00:05Z",
      "finished_at": "2026-04-10T13:00:25Z",
      "created_by": "admin_api",
      "dedupe_key": "graphics_generate:success1",
    },
    {
      "id": "mock-job-6",
      "job_type": "graphics_generate",
      "status": "success",
      "payload_json": "{\"data_key\":\"...\",\"chart_type\":\"area\"}",
      "result_json":
          "{\"publication_id\":43,\"cdn_url_lowres\":\"...\",\"version\":1}",
      "error_code": null,
      "error_message": null,
      "attempt_count": 1,
      "max_attempts": 3,
      "created_at": "2026-04-10T12:00:00Z",
      "started_at": "2026-04-10T12:00:05Z",
      "finished_at": "2026-04-10T12:00:25Z",
      "created_by": "admin_api",
      "dedupe_key": "graphics_generate:success2",
    },
    {
      "id": "mock-job-7",
      "job_type": "catalog_sync",
      "status": "failed",
      "payload_json": "{}",
      "result_json": null,
      "error_code": "STORAGE_ERROR",
      "error_message": "Failed to upload to S3",
      "attempt_count": 1,
      "max_attempts": 3,
      "created_at": "2026-04-10T11:00:00Z",
      "started_at": "2026-04-10T11:00:05Z",
      "finished_at": "2026-04-10T11:00:10Z",
      "created_by": "system",
      "dedupe_key": "catalog_sync:2026-04-09",
    },
    {
      "id": "mock-job-8",
      "job_type": "cube_fetch",
      "status": "failed",
      "payload_json": "{\"product_id\": \"14-10-0999-01\"}",
      "result_json": null,
      "error_code": "DATA_CONTRACT_VIOLATION",
      "error_message": "Missing required REF_DATE column",
      "attempt_count": 3,
      "max_attempts": 3,
      "created_at": "2026-04-10T10:00:00Z",
      "started_at": "2026-04-10T10:30:05Z",
      "finished_at": "2026-04-10T10:30:10Z",
      "created_by": "operator",
      "dedupe_key": "cube_fetch:14-10-0999-01",
    },
  ];
}
