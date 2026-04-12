import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/cube_repository.dart';
import '../domain/cube_catalog_entry.dart';
import '../domain/cube_search_response.dart';

/// Current search query entered by the user.
final cubeSearchQueryProvider = StateProvider<String>((ref) => '');

/// Debounced search results that react to [cubeSearchQueryProvider].
///
/// Waits 300 ms after the last query change before firing the API call.
/// If the query changes during the wait, the previous call is cancelled
/// automatically by Riverpod's `autoDispose`.
final cubeSearchResultsProvider =
    FutureProvider.autoDispose<CubeSearchResponse>((ref) async {
  final query = ref.watch(cubeSearchQueryProvider);

  if (query.trim().isEmpty) {
    return const CubeSearchResponse(items: [], total: 0);
  }

  // Debounce: wait 300 ms then check if we're still the active call.
  final cancelled = Completer<void>();
  ref.onDispose(() => cancelled.complete());

  await Future.any([
    Future.delayed(const Duration(milliseconds: 300)),
    cancelled.future,
  ]);

  // If this provider was disposed during the delay, bail out.
  if (cancelled.isCompleted) {
    throw StateError('Cancelled');
  }

  final repo = ref.read(cubeRepositoryProvider);
  return repo.search(query);
});

/// Fetches a single cube's full metadata by product ID.
final cubeDetailProvider = FutureProvider.autoDispose
    .family<CubeCatalogEntry, String>((ref, productId) async {
  final repo = ref.read(cubeRepositoryProvider);
  return repo.getByProductId(productId);
});
