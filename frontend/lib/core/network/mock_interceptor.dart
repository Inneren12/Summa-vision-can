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

  /// Tracks poll count for the mock fetch job to simulate running → success.
  int _fetchJobPollCount = 0;

  /// Tracks poll count per generation job_id for C-3 mock polling.
  final Map<String, int> _genJobPollCounts = {};

  MockInterceptor({this.enableDelay = true});

  static bool get isEnabled =>
      dotenv.env['USE_MOCK']?.toLowerCase() == 'true';

  @override
  void onRequest(
    RequestOptions options,
    RequestInterceptorHandler handler,
  ) {
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

    // Data preview: GET /admin/data/preview/*
    if (path.contains('/admin/data/preview/') && options.method == 'GET') {
      handler.resolve(
        Response(
          requestOptions: options,
          statusCode: 200,
          data: _dataPreviewFixture,
        ),
        true,
      );
      return;
    }

    // Fetch trigger: POST /admin/cubes/*/fetch
    if (path.contains('/fetch') && options.method == 'POST') {
      handler.resolve(
        Response(
          requestOptions: options,
          statusCode: 202,
          data: {'job_id': 456, 'status': 'queued', 'product_id': '13-10-0888-01'},
        ),
        true,
      );
      return;
    }

    // C-4: GET /admin/jobs (list) — must match before individual job routes
    if (path.contains('/admin/jobs') &&
        !path.contains('/admin/jobs/') &&
        options.method == 'GET') {
      handler.resolve(
        Response(
          requestOptions: options,
          statusCode: 200,
          data: _filteredJobsListFixture(options.queryParameters),
        ),
        true,
      );
      return;
    }

    // C-4: POST /admin/jobs/*/retry
    if (path.contains('/retry') &&
        path.contains('/admin/jobs/') &&
        options.method == 'POST') {
      handler.resolve(
        Response(
          requestOptions: options,
          statusCode: 202,
          data: {'job_id': 'mock-retry-job-001', 'status': 'queued'},
        ),
        true,
      );
      return;
    }

    // Job status: GET /admin/jobs/456
    if (path.contains('/admin/jobs/456')) {
      _fetchJobPollCount++;
      if (_fetchJobPollCount <= 2) {
        handler.resolve(
          Response(
            requestOptions: options,
            statusCode: 200,
            data: {
              'job_id': '456',
              'status': 'running',
            },
          ),
          true,
        );
      } else {
        handler.resolve(
          Response(
            requestOptions: options,
            statusCode: 200,
            data: {
              'job_id': '456',
              'status': 'success',
              'result_json':
                  '{"storage_key": "statcan/processed/13-10-0888-01/2024-12-15.parquet"}',
            },
          ),
          true,
        );
        _fetchJobPollCount = 0; // reset for next fetch cycle
      }
      return;
    }

    if (path.contains('/admin/cubes/sync') && options.method == 'POST') {
      handler.resolve(
        Response(
          requestOptions: options,
          statusCode: 202,
          data: {'job_id': 'mock-sync-job-123'},
        ),
        true,
      );
      return;
    }

    if (path.contains('/admin/cubes/search')) {
      handler.resolve(
        Response(
          requestOptions: options,
          statusCode: 200,
          data: _cubeSearchFixture,
        ),
        true,
      );
      return;
    }

    // Single cube detail: /admin/cubes/{product_id}
    final cubeDetailRegex = RegExp(r'/admin/cubes/[\d-]+');
    if (cubeDetailRegex.hasMatch(path) && options.method == 'GET') {
      handler.resolve(
        Response(
          requestOptions: options,
          statusCode: 200,
          data: _cubeDetailFixture,
        ),
        true,
      );
      return;
    }

    // C-5: GET /admin/kpi → KPI dashboard metrics
    if (path.contains('/admin/kpi') && options.method == 'GET') {
      handler.resolve(
        Response(
          requestOptions: options,
          statusCode: 200,
          data: _kpiFixture,
        ),
        true,
      );
      return;
    }

    if (path.contains('/admin/queue')) {
      handler.resolve(
        Response(
          requestOptions: options,
          statusCode: 200,
          data: _queueFixture,
        ),
        true,
      );
      return;
    }

    // C-3: POST /admin/graphics/generate → 202 with job_id
    if (path.contains('/admin/graphics/generate') &&
        options.method == 'POST') {
      handler.resolve(
        Response(
          requestOptions: options,
          statusCode: 202,
          data: {'job_id': 'mock-gen-job-789', 'status': 'queued'},
        ),
        true,
      );
      return;
    }

    // Legacy PR-24: GET /admin/tasks/* → immediate COMPLETED
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

    // C-3: GET /admin/jobs/mock-gen-job-789 → polling simulation
    if (path.contains('/admin/jobs/mock-gen-job-789')) {
      const jobId = 'mock-gen-job-789';
      _genJobPollCounts[jobId] = (_genJobPollCounts[jobId] ?? 0) + 1;
      final count = _genJobPollCounts[jobId]!;

      if (count <= 3) {
        handler.resolve(
          Response(
            requestOptions: options,
            statusCode: 200,
            data: {
              'job_id': jobId,
              'status': 'running',
              'result_json': null,
            },
          ),
          true,
        );
      } else {
        _genJobPollCounts[jobId] = 0; // reset for next cycle
        handler.resolve(
          Response(
            requestOptions: options,
            statusCode: 200,
            data: {
              'job_id': jobId,
              'status': 'success',
              'result_json':
                  '{"publication_id":1,"cdn_url_lowres":"https://placehold.co/1080x1080/141414/00E5FF?text=Mock+Chart","s3_key_highres":"publications/1/v1/abcd_highres.png","version":1}',
            },
          ),
          true,
        );
      }
      return;
    }

    // Catch-all: when USE_MOCK=true, NEVER let requests reach the network.
    // Return a mock 404 so missing fixtures are immediately obvious and
    // DioException [connection error] can never be produced from the mock
    // admin panel.
    handler.resolve(
      Response(
        requestOptions: options,
        statusCode: 404,
        data: {
          'error': 'MockInterceptor: no fixture for ${options.path}',
        },
      ),
      true,
    );
  }

  /// Applies [status] / [job_type] query-param filtering on top of
  /// [_jobsListFixture]. Values of `all`, empty string, or missing params
  /// return the full fixture list. Updates `total` to match filtered length
  /// so the Jobs Dashboard header count stays in sync.
  static Map<String, dynamic> _filteredJobsListFixture(
    Map<String, dynamic> queryParameters,
  ) {
    final fixture = _jobsListFixture;
    final items =
        List<Map<String, dynamic>>.from(fixture['items'] as List<dynamic>);

    final rawStatus = queryParameters['status']?.toString();
    final rawJobType = queryParameters['job_type']?.toString();

    final statusFilter = (rawStatus == null ||
            rawStatus.isEmpty ||
            rawStatus.toLowerCase() == 'all')
        ? null
        : rawStatus;
    final jobTypeFilter = (rawJobType == null ||
            rawJobType.isEmpty ||
            rawJobType.toLowerCase() == 'all')
        ? null
        : rawJobType;

    final filtered = items.where((job) {
      if (statusFilter != null && job['status'] != statusFilter) {
        return false;
      }
      if (jobTypeFilter != null && job['job_type'] != jobTypeFilter) {
        return false;
      }
      return true;
    }).toList();

    return {
      'items': filtered,
      'total': filtered.length,
    };
  }

  static const List<Map<String, dynamic>> _cubeSearchFixture = [
    {
      'product_id': '13-10-0888-01',
      'title_en': 'New housing price index, monthly',
      'title_fr': 'Indice des prix des logements neufs, mensuel',
      'subject_code': '18',
      'subject_en': 'Prices and price indexes',
      'frequency': 'Monthly',
      'start_date': '1981-01-01',
      'end_date': '2024-12-01',
      'archive_status': false,
    },
    {
      'product_id': '18-10-0004-01',
      'title_en': 'Consumer Price Index, monthly, not seasonally adjusted',
      'title_fr':
          "Indice des prix à la consommation, mensuel, non désaisonnalisé",
      'subject_code': '18',
      'subject_en': 'Prices and price indexes',
      'frequency': 'Monthly',
      'start_date': '1914-01-01',
      'end_date': '2024-11-01',
      'archive_status': false,
    },
    {
      'product_id': '14-10-0287-01',
      'title_en':
          'Labour force characteristics by province, monthly, seasonally adjusted',
      'title_fr':
          "Caractéristiques de la population active selon la province, mensuel, désaisonnalisé",
      'subject_code': '14',
      'subject_en': 'Labour',
      'frequency': 'Monthly',
      'start_date': '1976-01-01',
      'end_date': '2024-11-01',
      'archive_status': false,
    },
    {
      'product_id': '34-10-0145-01',
      'title_en': 'Canada Mortgage and Housing Corporation, housing starts',
      'title_fr':
          "Société canadienne d'hypothèques et de logement, mises en chantier",
      'subject_code': '34',
      'subject_en': 'International trade',
      'survey_en': 'Housing Starts Survey',
      'frequency': 'Quarterly',
      'start_date': '1990-01-01',
      'end_date': '2024-09-01',
      'archive_status': false,
    },
    {
      'product_id': '36-10-0402-01',
      'title_en':
          'Gross domestic product (GDP) at basic prices, by industry',
      'title_fr':
          "Produit intérieur brut (PIB) aux prix de base, par industrie",
      'subject_code': '36',
      'subject_en': 'Gross domestic product',
      'frequency': 'Monthly',
      'start_date': '1997-01-01',
      'end_date': '2024-09-01',
      'archive_status': true,
    },
  ];

  static const Map<String, dynamic> _cubeDetailFixture = {
    'product_id': '13-10-0888-01',
    'title_en': 'New housing price index, monthly',
    'title_fr': 'Indice des prix des logements neufs, mensuel',
    'subject_code': '18',
    'subject_en': 'Prices and price indexes',
    'survey_en': 'New Housing Price Index',
    'frequency': 'Monthly',
    'start_date': '1981-01-01',
    'end_date': '2024-12-01',
    'archive_status': false,
  };

  static const Map<String, dynamic> _dataPreviewFixture = {
    'storage_key': 'statcan/processed/13-10-0888-01/2024-12-15.parquet',
    'rows': 1500,
    'columns': 5,
    'column_names': ['REF_DATE', 'GEO', 'VALUE', 'SCALAR_ID', 'STATUS'],
    'data': [
      {'REF_DATE': '2024-01', 'GEO': 'Canada', 'VALUE': 156.2, 'SCALAR_ID': 0, 'STATUS': 'A'},
      {'REF_DATE': '2024-01', 'GEO': 'Ontario', 'VALUE': 162.1, 'SCALAR_ID': 0, 'STATUS': 'A'},
      {'REF_DATE': '2024-02', 'GEO': 'Canada', 'VALUE': 157.8, 'SCALAR_ID': 0, 'STATUS': 'A'},
      {'REF_DATE': '2024-02', 'GEO': 'Ontario', 'VALUE': 163.5, 'SCALAR_ID': 0, 'STATUS': 'A'},
      {'REF_DATE': '2024-03', 'GEO': 'Canada', 'VALUE': 159.1, 'SCALAR_ID': 0, 'STATUS': 'A'},
      {'REF_DATE': '2024-03', 'GEO': 'Quebec', 'VALUE': 148.3, 'SCALAR_ID': 0, 'STATUS': 'A'},
      {'REF_DATE': '2024-04', 'GEO': 'Canada', 'VALUE': null, 'SCALAR_ID': 0, 'STATUS': 'F'},
      {'REF_DATE': '2024-04', 'GEO': 'Ontario', 'VALUE': 165.0, 'SCALAR_ID': 0, 'STATUS': 'A'},
      {'REF_DATE': '2024-05', 'GEO': 'Canada', 'VALUE': 161.4, 'SCALAR_ID': 0, 'STATUS': 'A'},
      {'REF_DATE': '2024-05', 'GEO': 'Quebec', 'VALUE': 150.7, 'SCALAR_ID': 1, 'STATUS': 'A'},
    ],
  };

  static const Map<String, dynamic> _kpiFixture = {
    'total_publications': 45,
    'published_count': 42,
    'draft_count': 3,
    'total_leads': 156,
    'b2b_leads': 38,
    'education_leads': 12,
    'isp_leads': 8,
    'b2c_leads': 98,
    'esp_synced_count': 140,
    'esp_failed_permanent_count': 4,
    'emails_sent': 120,
    'tokens_created': 120,
    'tokens_activated': 89,
    'tokens_exhausted': 12,
    'total_jobs': 156,
    'jobs_succeeded': 142,
    'jobs_failed': 8,
    'jobs_queued': 3,
    'jobs_running': 1,
    'failed_by_type': {
      'graphics_generate': 3,
      'cube_fetch': 4,
      'catalog_sync': 1,
    },
    'catalog_syncs': 28,
    'data_contract_violations': 2,
    'period_start': '2026-03-13T00:00:00Z',
    'period_end': '2026-04-12T00:00:00Z',
  };

  static Map<String, dynamic> get _jobsListFixture {
    final now = DateTime.now().toUtc();
    final twoMinAgo = now.subtract(const Duration(minutes: 2));
    final fifteenMinAgo = now.subtract(const Duration(minutes: 15));

    return {
      'items': [
        // 1. Queued — catalog_sync
        {
          'id': 'job-001',
          'job_type': 'catalog_sync',
          'status': 'queued',
          'payload_json':
              '{"schema_version":1,"date":"2026-04-12"}',
          'result_json': null,
          'error_code': null,
          'error_message': null,
          'attempt_count': 0,
          'max_attempts': 3,
          'created_at': now.subtract(const Duration(minutes: 5)).toIso8601String(),
          'started_at': null,
          'finished_at': null,
          'created_by': 'scheduler',
          'dedupe_key': 'catalog_sync:2026-04-12',
        },
        // 2. Queued — cube_fetch
        {
          'id': 'job-002',
          'job_type': 'cube_fetch',
          'status': 'queued',
          'payload_json':
              '{"schema_version":1,"product_id":"13-10-0888-01","ref_date":"2026-04-01"}',
          'result_json': null,
          'error_code': null,
          'error_message': null,
          'attempt_count': 0,
          'max_attempts': 3,
          'created_at': now.subtract(const Duration(minutes: 4)).toIso8601String(),
          'started_at': null,
          'finished_at': null,
          'created_by': 'admin_api',
          'dedupe_key': 'fetch:13-10-0888-01:2026-04-01',
        },
        // 3. Running — graphics_generate, started 2 min ago (NOT stale)
        {
          'id': 'job-003',
          'job_type': 'graphics_generate',
          'status': 'running',
          'payload_json':
              '{"schema_version":1,"data_key":"statcan/processed/13-10-0888-01/2024-12-15.parquet","chart_type":"line","title":"Housing Prices","size":[1080,1080],"category":"housing"}',
          'result_json': null,
          'error_code': null,
          'error_message': null,
          'attempt_count': 1,
          'max_attempts': 3,
          'created_at': now.subtract(const Duration(minutes: 3)).toIso8601String(),
          'started_at': twoMinAgo.toIso8601String(),
          'finished_at': null,
          'created_by': 'admin_api',
          'dedupe_key':
              'graphics:13-10-0888-01:statcan/processed/13-10-0888-01/2024-12-15.parquet:abc123',
        },
        // 4. Running — cube_fetch, started 15 min ago (STALE/ZOMBIE)
        {
          'id': 'job-004',
          'job_type': 'cube_fetch',
          'status': 'running',
          'payload_json':
              '{"schema_version":1,"product_id":"18-10-0004-01","ref_date":"2026-04-01"}',
          'result_json': null,
          'error_code': null,
          'error_message': null,
          'attempt_count': 1,
          'max_attempts': 3,
          'created_at': now.subtract(const Duration(minutes: 20)).toIso8601String(),
          'started_at': fifteenMinAgo.toIso8601String(),
          'finished_at': null,
          'created_by': 'scheduler',
          'dedupe_key': 'fetch:18-10-0004-01:2026-04-01',
        },
        // 5. Success — graphics_generate with result_json
        {
          'id': 'job-005',
          'job_type': 'graphics_generate',
          'status': 'success',
          'payload_json':
              '{"schema_version":1,"data_key":"statcan/processed/13-10-0888-01/2024-12-15.parquet","chart_type":"bar","title":"Housing Index","size":[1080,1080],"category":"housing"}',
          'result_json':
              '{"publication_id":42,"cdn_url_lowres":"https://cdn.example.com/pub/42/v1/lowres.png","s3_key_highres":"publications/42/v1/highres.png","version":1}',
          'error_code': null,
          'error_message': null,
          'attempt_count': 1,
          'max_attempts': 3,
          'created_at': now.subtract(const Duration(hours: 1)).toIso8601String(),
          'started_at':
              now.subtract(const Duration(hours: 1)).toIso8601String(),
          'finished_at':
              now.subtract(const Duration(minutes: 59, seconds: 36)).toIso8601String(),
          'created_by': 'admin_api',
          'dedupe_key':
              'graphics:13-10-0888-01:statcan/processed/13-10-0888-01/2024-12-15.parquet:def456',
        },
        // 6. Success — graphics_generate with result_json (#2)
        {
          'id': 'job-006',
          'job_type': 'graphics_generate',
          'status': 'success',
          'payload_json':
              '{"schema_version":1,"data_key":"statcan/processed/14-10-0287-01/2026-03-01.parquet","chart_type":"line","title":"Labour Force","size":[1200,628],"category":"labour"}',
          'result_json':
              '{"publication_id":43,"cdn_url_lowres":"https://cdn.example.com/pub/43/v1/lowres.png","s3_key_highres":"publications/43/v1/highres.png","version":1}',
          'error_code': null,
          'error_message': null,
          'attempt_count': 1,
          'max_attempts': 3,
          'created_at': now.subtract(const Duration(hours: 2)).toIso8601String(),
          'started_at':
              now.subtract(const Duration(hours: 2)).toIso8601String(),
          'finished_at':
              now.subtract(const Duration(hours: 1, minutes: 59, seconds: 35)).toIso8601String(),
          'created_by': 'admin_api',
          'dedupe_key': null,
        },
        // 7. Failed — retryable (STORAGE_ERROR, attempt 1/3)
        {
          'id': 'job-007',
          'job_type': 'graphics_generate',
          'status': 'failed',
          'payload_json':
              '{"schema_version":1,"data_key":"statcan/processed/36-10-0402-01/2026-01-01.parquet","chart_type":"area","title":"GDP by Industry","size":[1080,1080],"category":"economy"}',
          'result_json': null,
          'error_code': 'STORAGE_ERROR',
          'error_message':
              'S3 upload failed: NoSuchBucket — the specified bucket does not exist. Ensure the MinIO bucket "publications" has been created.',
          'attempt_count': 1,
          'max_attempts': 3,
          'created_at': now.subtract(const Duration(hours: 3)).toIso8601String(),
          'started_at':
              now.subtract(const Duration(hours: 3)).toIso8601String(),
          'finished_at':
              now.subtract(const Duration(hours: 2, minutes: 59, seconds: 50)).toIso8601String(),
          'created_by': 'admin_api',
          'dedupe_key':
              'graphics:36-10-0402-01:statcan/processed/36-10-0402-01/2026-01-01.parquet:ghi789',
        },
        // 8. Failed — non-retryable (DATA_CONTRACT_VIOLATION, attempt 3/3)
        {
          'id': 'job-008',
          'job_type': 'cube_fetch',
          'status': 'failed',
          'payload_json':
              '{"schema_version":1,"product_id":"34-10-0145-01","ref_date":"2026-03-01"}',
          'result_json': null,
          'error_code': 'DATA_CONTRACT_VIOLATION',
          'error_message':
              'Column REF_DATE missing from StatCan response. Expected columns: [REF_DATE, GEO, VALUE]. Got: [DATE, GEOGRAPHY, AMOUNT]. Data contract mismatch — manual intervention required.',
          'attempt_count': 3,
          'max_attempts': 3,
          'created_at': now.subtract(const Duration(hours: 5)).toIso8601String(),
          'started_at':
              now.subtract(const Duration(hours: 5)).toIso8601String(),
          'finished_at':
              now.subtract(const Duration(hours: 4, minutes: 59, seconds: 55)).toIso8601String(),
          'created_by': 'scheduler',
          'dedupe_key': 'fetch:34-10-0145-01:2026-03-01',
        },
      ],
      'total': 8,
    };
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
      'headline': 'Bank of Canada holds rates steady for 3rd consecutive meeting',
      'chart_type': 'AREA',
      'virality_score': 7.2,
      'status': 'DRAFT',
      'created_at': '2026-03-17T09:00:00Z',
    },
  ];
}
