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
      final options = RequestOptions(path: '/api/v1/admin/graphics/generate');
      final completer = Completer<Response>();

      interceptor.onRequest(
        options,
        _CapturingHandler(onResolve: completer.complete),
      );

      await Future.delayed(Duration.zero);

      final captured = await completer.future;
      expect(captured.statusCode, equals(202));
      expect((captured.data as Map)['task_id'], isNotNull);
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
  });
}

/// Test helper: captures the resolved response from a RequestInterceptorHandler.
class _CapturingHandler extends RequestInterceptorHandler {
  final void Function(Response) onResolve;

  _CapturingHandler({required this.onResolve});

  @override
  void resolve(
    Response response, [
    bool callFollowingResponseInterceptor = false,
  ]) {
    onResolve(response);
  }

  @override
  void next(RequestOptions options) {}
}
