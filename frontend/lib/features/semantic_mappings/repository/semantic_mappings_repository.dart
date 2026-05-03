import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/dio_client.dart';
import '../models/semantic_mapping.dart';

/// Phase 3.1b admin client for the semantic-mapping CRUD endpoints.
class SemanticMappingsRepository {
  SemanticMappingsRepository(this._dio);

  final Dio _dio;

  Future<SemanticMappingListPage> list({
    String? cubeId,
    String? semanticKey,
    bool? isActive,
    int limit = 50,
    int offset = 0,
  }) async {
    final response = await _dio.get(
      '/api/v1/admin/semantic-mappings',
      queryParameters: {
        if (cubeId != null && cubeId.isNotEmpty) 'cube_id': cubeId,
        if (semanticKey != null && semanticKey.isNotEmpty)
          'semantic_key': semanticKey,
        if (isActive != null) 'is_active': isActive,
        'limit': limit,
        'offset': offset,
      },
    );
    return SemanticMappingListPage.fromJson(
      Map<String, dynamic>.from(response.data as Map),
    );
  }

  Future<SemanticMapping> getById(int id) async {
    final response = await _dio.get('/api/v1/admin/semantic-mappings/$id');
    return SemanticMapping.fromJson(
      Map<String, dynamic>.from(response.data as Map),
    );
  }

  /// Returns ``(mapping, wasCreated)`` so the caller can show distinct
  /// snackbars for create vs. update outcomes.
  Future<(SemanticMapping, bool)> upsert({
    required String cubeId,
    required int productId,
    required String semanticKey,
    required String label,
    String? description,
    required Map<String, dynamic> config,
    required bool isActive,
    String? updatedBy,
    int? ifMatchVersion,
  }) async {
    final response = await _dio.post(
      '/api/v1/admin/semantic-mappings/upsert',
      data: {
        'cube_id': cubeId,
        'product_id': productId,
        'semantic_key': semanticKey,
        'label': label,
        if (description != null) 'description': description,
        'config': config,
        'is_active': isActive,
        if (updatedBy != null) 'updated_by': updatedBy,
        if (ifMatchVersion != null) 'if_match_version': ifMatchVersion,
      },
      options: Options(
        validateStatus: (code) => code != null && code >= 200 && code < 300,
        headers: ifMatchVersion != null
            ? {'If-Match': ifMatchVersion.toString()}
            : null,
      ),
    );
    final wasCreated = response.statusCode == 201;
    return (
      SemanticMapping.fromJson(
        Map<String, dynamic>.from(response.data as Map),
      ),
      wasCreated,
    );
  }

  Future<SemanticMapping> softDelete(int id) async {
    final response = await _dio.delete('/api/v1/admin/semantic-mappings/$id');
    return SemanticMapping.fromJson(
      Map<String, dynamic>.from(response.data as Map),
    );
  }

  /// Reads the cached cube metadata. Returns null on 404 so the caller
  /// can render a non-blocking "not yet cached" hint without throwing.
  Future<CubeMetadataSnapshot?> getCubeMetadata(
    String cubeId, {
    bool prime = false,
    int? productId,
  }) async {
    try {
      final response = await _dio.get(
        '/api/v1/admin/cube-metadata/$cubeId',
        queryParameters: {
          if (prime) 'prime': true,
          if (productId != null) 'product_id': productId,
        },
      );
      return CubeMetadataSnapshot.fromJson(
        Map<String, dynamic>.from(response.data as Map),
      );
    } on DioException catch (error) {
      if (error.response?.statusCode == 404) {
        return null;
      }
      rethrow;
    }
  }
}
