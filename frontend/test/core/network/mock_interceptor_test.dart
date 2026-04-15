import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:summa_vision_admin/core/network/mock_interceptor.dart';

void main() {
  setUpAll(() {
    dotenv.testLoad(mergeWith: {'USE_MOCK': 'true'});
  });

  group('MockInterceptor.isEnabled', () {
    test('returns true when USE_MOCK=true', () {
      expect(MockInterceptor.isEnabled, isTrue);
    });
  });

  group('MockInterceptor responses', () {
    late MockInterceptor interceptor;

    setUp(() {
      interceptor = MockInterceptor(enableDelay: false);
    });

    test('returns queue fixture for /admin/queue', () async {
      final options = RequestOptions(path: '/api/v1/admin/queue');
      final completer = Completer<Response>();

      interceptor.onRequest(
        options,
        _CapturingHandler(onResolve: completer.complete),
      );

      // Allow microtasks to flush (no real delay because enableDelay=false)
      await Future.delayed(Duration.zero);

      final captured = await completer.future;
      expect(captured.statusCode, equals(200));
      expect(captured.data, isList);
      expect((captured.data as List).length, equals(3));
    });

    test('queue fixture contains required fields', () async {
      final options = RequestOptions(path: '/api/v1/admin/queue');
      final completer = Completer<Response>();

      interceptor.onRequest(
        options,
        _CapturingHandler(onResolve: completer.complete),
      );

      await Future.delayed(Duration.zero);

      final captured = await completer.future;
      final first = (captured.data as List).first as Map<String, dynamic>;
      expect(first.containsKey('id'), isTrue);
      expect(first.containsKey('headline'), isTrue);
      expect(first.containsKey('virality_score'), isTrue);
      expect(first.containsKey('chart_type'), isTrue);
      expect(first.containsKey('status'), isTrue);
    });

    test('returns 202 for /admin/graphics/generate', () async {
      final options = RequestOptions(
        path: '/api/v1/admin/graphics/generate',
        method: 'POST',
      );
      final completer = Completer<Response>();

      interceptor.onRequest(
        options,
        _CapturingHandler(onResolve: completer.complete),
      );

      await Future.delayed(Duration.zero);

      final captured = await completer.future;
      expect(captured.statusCode, equals(202));
      expect((captured.data as Map)['job_id'], isNotNull);
    });

    test('returns COMPLETED status for /admin/tasks/', () async {
      final options = RequestOptions(path: '/api/v1/admin/tasks/mock-uuid');
      final completer = Completer<Response>();

      interceptor.onRequest(
        options,
        _CapturingHandler(onResolve: completer.complete),
      );

      await Future.delayed(Duration.zero);

      final captured = await completer.future;
      expect(captured.statusCode, equals(200));
      expect((captured.data as Map)['status'], equals('COMPLETED'));
    });

    test('returns jobs list for /admin/jobs with no filters', () async {
      final options = RequestOptions(
        path: '/api/v1/admin/jobs',
        method: 'GET',
      );
      final completer = Completer<Response>();

      interceptor.onRequest(
        options,
        _CapturingHandler(onResolve: completer.complete),
      );

      await Future.delayed(Duration.zero);

      final captured = await completer.future;
      expect(captured.statusCode, equals(200));
      final data = captured.data as Map<String, dynamic>;
      expect(data['items'], isList);
      expect((data['items'] as List).isNotEmpty, isTrue);
      expect(data['total'], equals((data['items'] as List).length));
      final first = (data['items'] as List).first as Map<String, dynamic>;
      // Must match Dart model field names (snake_case alias keys).
      expect(first.containsKey('id'), isTrue);
      expect(first.containsKey('job_type'), isTrue);
      expect(first.containsKey('status'), isTrue);
      expect(first.containsKey('attempt_count'), isTrue);
      expect(first.containsKey('max_attempts'), isTrue);
      expect(first.containsKey('created_at'), isTrue);
    });

    test('filters jobs by status=failed', () async {
      final options = RequestOptions(
        path: '/api/v1/admin/jobs',
        method: 'GET',
        queryParameters: {'status': 'failed'},
      );
      final completer = Completer<Response>();

      interceptor.onRequest(
        options,
        _CapturingHandler(onResolve: completer.complete),
      );

      await Future.delayed(Duration.zero);

      final captured = await completer.future;
      expect(captured.statusCode, equals(200));
      final data = captured.data as Map<String, dynamic>;
      final items = data['items'] as List;
      expect(items, isNotEmpty);
      for (final item in items) {
        expect((item as Map)['status'], equals('failed'));
      }
      expect(data['total'], equals(items.length));
    });

    test('filters jobs by job_type=cube_fetch', () async {
      final options = RequestOptions(
        path: '/api/v1/admin/jobs',
        method: 'GET',
        queryParameters: {'job_type': 'cube_fetch'},
      );
      final completer = Completer<Response>();

      interceptor.onRequest(
        options,
        _CapturingHandler(onResolve: completer.complete),
      );

      await Future.delayed(Duration.zero);

      final captured = await completer.future;
      final items = (captured.data as Map)['items'] as List;
      expect(items, isNotEmpty);
      for (final item in items) {
        expect((item as Map)['job_type'], equals('cube_fetch'));
      }
    });

    test('status=all returns the full jobs list', () async {
      final optionsAll = RequestOptions(
        path: '/api/v1/admin/jobs',
        method: 'GET',
        queryParameters: {'status': 'all'},
      );
      final optionsNone = RequestOptions(
        path: '/api/v1/admin/jobs',
        method: 'GET',
      );

      final allCompleter = Completer<Response>();
      final noneCompleter = Completer<Response>();

      interceptor.onRequest(
        optionsAll,
        _CapturingHandler(onResolve: allCompleter.complete),
      );
      interceptor.onRequest(
        optionsNone,
        _CapturingHandler(onResolve: noneCompleter.complete),
      );

      await Future.delayed(Duration.zero);

      final allLen =
          ((await allCompleter.future).data as Map)['items'].length as int;
      final noneLen =
          ((await noneCompleter.future).data as Map)['items'].length as int;
      expect(allLen, equals(noneLen));
    });

    test('returns KPI fixture for /admin/kpi', () async {
      final options = RequestOptions(
        path: '/api/v1/admin/kpi',
        method: 'GET',
      );
      final completer = Completer<Response>();

      interceptor.onRequest(
        options,
        _CapturingHandler(onResolve: completer.complete),
      );

      await Future.delayed(Duration.zero);

      final captured = await completer.future;
      expect(captured.statusCode, equals(200));
      final data = captured.data as Map<String, dynamic>;
      // Required by Dart KPIData model (`@JsonKey(name: ...)`).
      const requiredKeys = [
        'total_publications',
        'published_count',
        'draft_count',
        'total_leads',
        'b2b_leads',
        'education_leads',
        'isp_leads',
        'b2c_leads',
        'esp_synced_count',
        'esp_failed_permanent_count',
        'emails_sent',
        'tokens_created',
        'tokens_activated',
        'tokens_exhausted',
        'total_jobs',
        'jobs_succeeded',
        'jobs_failed',
        'jobs_queued',
        'jobs_running',
        'failed_by_type',
        'catalog_syncs',
        'data_contract_violations',
        'period_start',
        'period_end',
      ];
      for (final key in requiredKeys) {
        expect(data.containsKey(key), isTrue,
            reason: 'KPI fixture missing key: $key');
      }
    });

    test('returns 404 catch-all for unmatched endpoints', () async {
      final options = RequestOptions(
        path: '/api/v1/admin/unknown-endpoint',
        method: 'GET',
      );
      final completer = Completer<Response>();

      interceptor.onRequest(
        options,
        _CapturingHandler(
          onResolve: completer.complete,
          onNext: (_) => completer.completeError(
            StateError('catch-all passed through instead of resolving 404'),
          ),
        ),
      );

      await Future.delayed(Duration.zero);

      final captured = await completer.future;
      expect(captured.statusCode, equals(404));
      final data = captured.data as Map<String, dynamic>;
      expect(data['error'], contains('MockInterceptor'));
      expect(data['error'], contains('/api/v1/admin/unknown-endpoint'));
    });
  });

  group('MockInterceptor delay', () {
    test('delays mock responses by at least ~900ms when delay is enabled',
        () async {
      // Dedicated interceptor instance WITH delay enabled.
      final delayedInterceptor = MockInterceptor();
      final options = RequestOptions(path: '/api/v1/admin/queue');
      final completer = Completer<Response>();
      final stopwatch = Stopwatch()..start();

      delayedInterceptor.onRequest(
        options,
        _CapturingHandler(onResolve: completer.complete),
      );

      await completer.future;
      stopwatch.stop();

      expect(
        stopwatch.elapsedMilliseconds,
        greaterThanOrEqualTo(900),
        reason:
            'Mock responses MUST include the 1s Future.delayed so loading states are visible',
      );
    });
  });
}

/// Test helper: captures the resolved response from a RequestInterceptorHandler.
class _CapturingHandler extends RequestInterceptorHandler {
  final void Function(Response) onResolve;
  final void Function(RequestOptions)? onNext;

  _CapturingHandler({required this.onResolve, this.onNext});

  @override
  void resolve(Response response, [bool callFollowingResponseInterceptor = false]) {
    onResolve(response);
  }

  @override
  void next(RequestOptions options) {
    onNext?.call(options);
  }
}
