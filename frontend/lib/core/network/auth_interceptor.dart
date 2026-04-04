import 'package:dio/dio.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';

/// Injects [X-API-KEY] header into every outgoing request.
class AuthInterceptor extends Interceptor {
  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) {
    final apiKey = dotenv.env['ADMIN_API_KEY'] ?? '';
    options.headers['X-API-KEY'] = apiKey;
    handler.next(options);
  }
}
