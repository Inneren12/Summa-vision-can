import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/dio_client.dart';
import '../domain/task_status.dart';

class GraphicRepository {
  GraphicRepository(this._dio);

  final Dio _dio;

  /// POST /api/v1/admin/graphics/generate
  /// Returns the task_id from the 202 response.
  Future<String> submitGeneration({
    required int briefId,
    String sizePreset = 'twitter',
    int dpi = 150,
    bool watermark = true,
  }) async {
    final response = await _dio.post<Map<String, dynamic>>(
      '/api/v1/admin/graphics/generate',
      data: {
        'brief_id': briefId,
        'size_preset': sizePreset,
        'dpi': dpi,
        'watermark': watermark,
      },
    );
    final taskId = response.data?['task_id'] as String?;
    if (taskId == null) throw Exception('No task_id in response');
    return taskId;
  }

  /// GET /api/v1/admin/tasks/{taskId}
  Future<TaskStatus> getTaskStatus(String taskId) async {
    final response = await _dio.get<Map<String, dynamic>>(
      '/api/v1/admin/tasks/$taskId',
    );
    return TaskStatus.fromJson(response.data!);
  }
}

final graphicRepositoryProvider = Provider<GraphicRepository>(
  (ref) => GraphicRepository(ref.watch(dioProvider)),
);
