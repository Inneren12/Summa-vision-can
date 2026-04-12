import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/dio_client.dart';
import '../domain/graphics_generate_request.dart';
import '../domain/job_status.dart';

/// Repository for the C-3 chart generation flow.
///
/// Submits generation requests and polls job status via the B-4 API.
class GraphicGenerationRepository {
  GraphicGenerationRepository(this._dio);

  final Dio _dio;

  /// POST /api/v1/admin/graphics/generate → 202 with job_id.
  Future<String> submitGeneration(GraphicsGenerateRequest request) async {
    final response = await _dio.post(
      '/api/v1/admin/graphics/generate',
      data: request.toJson(),
    );
    return response.data['job_id'] as String;
  }

  /// GET /api/v1/admin/jobs/{jobId} → JobStatus.
  Future<JobStatus> getJobStatus(String jobId) async {
    final response = await _dio.get('/api/v1/admin/jobs/$jobId');
    return JobStatus.fromJson(response.data as Map<String, dynamic>);
  }
}

final graphicGenerationRepositoryProvider =
    Provider<GraphicGenerationRepository>(
  (ref) => GraphicGenerationRepository(ref.watch(dioProvider)),
);
