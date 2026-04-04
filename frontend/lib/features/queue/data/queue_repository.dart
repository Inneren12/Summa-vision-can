import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/dio_client.dart';
import '../domain/content_brief.dart';

class QueueRepository {
  QueueRepository(this._dio);

  final Dio _dio;

  /// Fetch DRAFT briefs from [GET /api/v1/admin/queue].
  Future<List<ContentBrief>> fetchQueue({int limit = 20}) async {
    final response = await _dio.get<List<dynamic>>(
      '/api/v1/admin/queue',
      queryParameters: {'limit': limit},
    );
    final data = response.data ?? [];
    return data
        .map((e) => ContentBrief.fromJson(e as Map<String, dynamic>))
        .toList();
  }
}

/// Riverpod provider for [QueueRepository].
final queueRepositoryProvider = Provider<QueueRepository>(
  (ref) => QueueRepository(ref.watch(dioProvider)),
);

/// FutureProvider that fetches the current queue.
/// Invalidating this provider triggers a re-fetch.
final queueProvider = FutureProvider<List<ContentBrief>>((ref) {
  return ref.watch(queueRepositoryProvider).fetchQueue();
});
