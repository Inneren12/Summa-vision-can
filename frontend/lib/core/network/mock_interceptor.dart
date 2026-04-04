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
