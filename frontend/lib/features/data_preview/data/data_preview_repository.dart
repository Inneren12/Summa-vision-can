import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/dio_client.dart';
import '../domain/data_preview_response.dart';

/// Repository for the data preview and fetch endpoints (A-7).
class DataPreviewRepository {
  DataPreviewRepository(this._dio);

  final Dio _dio;

  /// Fetch a preview of a processed Parquet file.
  ///
  /// [storageKey] is the S3 key, e.g. `statcan/processed/13-10-0888-01/2024-12-15.parquet`.
  /// Backend enforces R15 cap: max 100 rows regardless of [limit].
  Future<DataPreviewResponse> getPreview(
    String storageKey, {
    int limit = 100,
  }) async {
    final response = await _dio.get(
      '/api/v1/admin/data/preview/${Uri.encodeComponent(storageKey)}',
      queryParameters: {'limit': limit},
    );
    return DataPreviewResponse.fromJson(
      response.data as Map<String, dynamic>,
    );
  }

  /// Trigger a data fetch job for [productId].
  ///
  /// Returns the job ID from the 202 response.
  /// Dedupe: same product_id same day returns existing job.
  Future<String> triggerFetch(String productId) async {
    final response = await _dio.post('/api/v1/admin/cubes/$productId/fetch');
    final data = response.data as Map<String, dynamic>;
    return data['job_id'].toString();
  }

  /// Poll job status via `GET /api/v1/admin/jobs/{jobId}`.
  ///
  /// Returns the full job status map so callers can inspect
  /// `status`, `result_json`, `error`, etc.
  Future<Map<String, dynamic>> getJobStatus(String jobId) async {
    final response = await _dio.get('/api/v1/admin/jobs/$jobId');
    return response.data as Map<String, dynamic>;
  }
}

/// Riverpod provider for [DataPreviewRepository].
final dataPreviewRepositoryProvider = Provider<DataPreviewRepository>(
  (ref) => DataPreviewRepository(ref.watch(dioProvider)),
);
