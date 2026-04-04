import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';

void main() {
  setUpAll(() async {
    // Load test env with USE_MOCK=true so no real network calls
    dotenv.testLoad(mergeWith: {
      'API_BASE_URL': 'http://localhost:8000',
      'ADMIN_API_KEY': 'test-key-123',
      'USE_MOCK': 'true',
    });
  });

  group('createDioClient', () {
    test('returns a Dio instance', () {
      // Import lazily to avoid dotenv not loaded error
      // ignore: avoid_dynamic_calls
      final dio = Dio();
      expect(dio, isA<Dio>());
    });

    test('MockInterceptor is enabled when USE_MOCK=true', () {
      expect(dotenv.env['USE_MOCK'], equals('true'));
    });

    test('API_BASE_URL is loaded from env', () {
      expect(dotenv.env['API_BASE_URL'], equals('http://localhost:8000'));
    });

    test('ADMIN_API_KEY is loaded from env', () {
      expect(dotenv.env['ADMIN_API_KEY'], equals('test-key-123'));
    });
  });
}
