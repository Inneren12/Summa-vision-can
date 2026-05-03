import 'package:dio/dio.dart';

/// Dart equivalent of frontend-public's ``extractBackendErrorPayload``.
///
/// Backend emits two envelope shapes:
///   1. Nested (standard for admin endpoints):
///        { "detail": { "error_code": "...", "message": "...", "details": {...} } }
///   2. Flat (auth middleware + global SummaVisionError):
///        { "error_code": "...", "message": "...", "detail": "..." }
///
/// The extractor checks nested first, then flat. Unknown shapes return a
/// payload with [errorCode] = null so callers can fall back to a generic
/// error.
class BackendErrorPayload {
  const BackendErrorPayload({
    required this.errorCode,
    required this.message,
    required this.details,
  });

  final String? errorCode;
  final String? message;
  final Map<String, dynamic>? details;

  bool get hasCode => errorCode != null;

  /// Pull a per-field error list out of [details] if present, else null.
  ///
  /// Backend nests a list at ``details.errors``; each entry has
  /// ``error_code``, ``dimension_name``, ``member_name``, ``message``,
  /// and (optionally) ``suggested_member_name_en``.
  List<Map<String, dynamic>>? get fieldErrors {
    if (details == null) return null;
    final raw = details!['errors'];
    if (raw is List) {
      return raw
          .whereType<Map<String, dynamic>>()
          .toList(growable: false);
    }
    return null;
  }

  static const empty = BackendErrorPayload(
    errorCode: null,
    message: null,
    details: null,
  );

  factory BackendErrorPayload.fromDioException(DioException error) {
    final data = error.response?.data;
    if (data is Map) {
      return _fromMap(Map<String, dynamic>.from(data));
    }
    return empty;
  }

  static BackendErrorPayload _fromMap(Map<String, dynamic> body) {
    // 1. Nested envelope: { detail: { error_code, message, details? } }
    final detail = body['detail'];
    if (detail is Map) {
      final detailMap = Map<String, dynamic>.from(detail);
      final code = detailMap['error_code'];
      if (code is String) {
        final message = detailMap['message'];
        final details = detailMap['details'];
        return BackendErrorPayload(
          errorCode: code,
          message: message is String ? message : null,
          details: details is Map ? Map<String, dynamic>.from(details) : null,
        );
      }
    }
    // 2. Flat envelope.
    final flatCode = body['error_code'];
    if (flatCode is String) {
      final message = body['message'] ?? body['error'] ?? body['detail'];
      return BackendErrorPayload(
        errorCode: flatCode,
        message: message is String ? message : null,
        details: null,
      );
    }
    return empty;
  }
}
