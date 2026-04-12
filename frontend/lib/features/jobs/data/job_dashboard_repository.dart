import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/dio_client.dart';
import '../domain/job.dart';
import '../domain/job_list_response.dart';

class JobDashboardRepository {
  final Dio _dio;

  JobDashboardRepository(this._dio);

  Future<JobListResponse> listJobs({
    String? jobType,
    String? status,
    int limit = 50,
  }) async {
    final response = await _dio.get(
      '/api/v1/admin/jobs',
      queryParameters: {
        if (jobType != null) 'job_type': jobType,
        if (status != null) 'status': status,
        'limit': limit,
      },
    );
    return JobListResponse.fromJson(response.data as Map<String, dynamic>);
  }

  Future<Job> getJob(String jobId) async {
    final response = await _dio.get('/api/v1/admin/jobs/$jobId');
    return Job.fromJson(response.data as Map<String, dynamic>);
  }

  Future<String> retryJob(String jobId) async {
    final response = await _dio.post('/api/v1/admin/jobs/$jobId/retry');
    return (response.data as Map<String, dynamic>)['job_id'] as String;
  }
}

final jobDashboardRepositoryProvider = Provider<JobDashboardRepository>(
  (ref) => JobDashboardRepository(ref.watch(dioProvider)),
);
