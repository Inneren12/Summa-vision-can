import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/dio_client.dart';
import '../models/semantic_mapping.dart';
import '../repository/semantic_mappings_repository.dart';

/// Riverpod provider for the admin semantic-mappings repository.
///
/// Declared here (not in the repository file) so screens that only
/// import ``providers/...`` can resolve the symbol — Dart does not
/// re-export across imports. Mirrors the pattern from
/// ``features/jobs/data/job_dashboard_repository.dart``.
final semanticMappingsRepositoryProvider =
    Provider<SemanticMappingsRepository>(
  (ref) => SemanticMappingsRepository(ref.watch(dioProvider)),
);

class SemanticMappingsFilter {
  const SemanticMappingsFilter({
    this.cubeId,
    this.semanticKey,
    this.isActive,
    this.limit = 50,
    this.offset = 0,
  });

  final String? cubeId;
  final String? semanticKey;
  final bool? isActive;
  final int limit;
  final int offset;

  SemanticMappingsFilter copyWith({
    String? cubeId,
    String? semanticKey,
    bool? isActive,
    int? limit,
    int? offset,
    bool clearCubeId = false,
    bool clearSemanticKey = false,
    bool clearIsActive = false,
  }) {
    return SemanticMappingsFilter(
      cubeId: clearCubeId ? null : (cubeId ?? this.cubeId),
      semanticKey:
          clearSemanticKey ? null : (semanticKey ?? this.semanticKey),
      isActive: clearIsActive ? null : (isActive ?? this.isActive),
      limit: limit ?? this.limit,
      offset: offset ?? this.offset,
    );
  }
}

final semanticMappingsFilterProvider =
    StateProvider<SemanticMappingsFilter>(
  (ref) => const SemanticMappingsFilter(),
);

final semanticMappingsListProvider =
    FutureProvider.autoDispose<SemanticMappingListPage>((ref) async {
  final filter = ref.watch(semanticMappingsFilterProvider);
  final repo = ref.read(semanticMappingsRepositoryProvider);
  return repo.list(
    cubeId: filter.cubeId,
    semanticKey: filter.semanticKey,
    isActive: filter.isActive,
    limit: filter.limit,
    offset: filter.offset,
  );
});

final semanticMappingProvider =
    FutureProvider.autoDispose.family<SemanticMapping, int>((ref, id) async {
  final repo = ref.read(semanticMappingsRepositoryProvider);
  return repo.getById(id);
});

/// Read-only cube metadata provider (default ?prime=false). Returns null
/// for cubes not yet cached so the form can render a non-blocking hint.
final cubeMetadataProvider = FutureProvider.autoDispose
    .family<CubeMetadataSnapshot?, String>((ref, cubeId) async {
  if (cubeId.trim().isEmpty) return null;
  final repo = ref.read(semanticMappingsRepositoryProvider);
  return repo.getCubeMetadata(cubeId);
});
