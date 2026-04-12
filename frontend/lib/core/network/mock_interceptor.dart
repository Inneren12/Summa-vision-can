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

    if (path.contains('/admin/graphics/generate')) {
      handler.resolve(
        Response(
          requestOptions: options,
          statusCode: 202,
          data: {'task_id': 'mock-task-uuid-1234', 'message': 'Generation started'},
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

    // Pass through any unmatched routes
    handler.next(options);
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
