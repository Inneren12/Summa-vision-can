import 'package:dio/dio.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'auth_interceptor.dart';
import 'mock_interceptor.dart';

/// Creates and configures the [Dio] HTTP client.
///
/// If [MockInterceptor.isEnabled] is true (USE_MOCK=true in .env),
/// requests are intercepted and served from local fixtures.
/// Otherwise, [AuthInterceptor] injects the X-API-KEY header on every
/// real request to the backend.
Dio createDioClient() {
  final baseUrl = dotenv.env['API_BASE_URL'] ?? 'http://localhost:8000';

  final dio = Dio(
    BaseOptions(
      baseUrl: baseUrl,
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 30),
      headers: {'Content-Type': 'application/json'},
    ),
  );

  if (MockInterceptor.isEnabled) {
    dio.interceptors.add(MockInterceptor());
  } else {
    dio.interceptors.add(AuthInterceptor());
  }

  return dio;
}

/// Riverpod provider for the shared [Dio] instance.
final dioProvider = Provider<Dio>((ref) => createDioClient());
