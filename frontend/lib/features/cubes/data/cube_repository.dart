import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/dio_client.dart';
import '../domain/cube_catalog_entry.dart';

class CubeRepository {
  CubeRepository(this._dio);

  final Dio _dio;

  /// Search cubes via [GET /api/v1/admin/cubes/search].
  ///
  /// The backend returns a plain JSON array (not a wrapped object).
  Future<List<CubeCatalogEntry>> search(String query, {int limit = 20}) async {
    final response = await _dio.get(
      '/api/v1/admin/cubes/search',
      queryParameters: {'q': query, 'limit': limit},
    );
    final list = response.data as List<dynamic>;
    return list
        .map((item) => CubeCatalogEntry.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  /// Fetch a single cube by product ID via [GET /api/v1/admin/cubes/:id].
  Future<CubeCatalogEntry> getByProductId(String productId) async {
    final response = await _dio.get('/api/v1/admin/cubes/$productId');
    return CubeCatalogEntry.fromJson(
      response.data as Map<String, dynamic>,
    );
  }

  /// Trigger a catalog sync via [POST /api/v1/admin/cubes/sync].
  Future<String> triggerSync() async {
    final response = await _dio.post('/api/v1/admin/cubes/sync');
    return (response.data as Map<String, dynamic>)['job_id'] as String;
  }
}

/// Riverpod provider for [CubeRepository].
final cubeRepositoryProvider = Provider<CubeRepository>(
  (ref) => CubeRepository(ref.watch(dioProvider)),
);
