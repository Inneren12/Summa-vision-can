import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/cube_repository.dart';
import '../domain/cube_catalog_entry.dart';

/// Current search query entered by the user.
final cubeSearchQueryProvider = StateProvider<String>((ref) => '');

/// Debounced search results that react to [cubeSearchQueryProvider].
///
/// Waits 300 ms after the last query change before firing the API call.
/// If the query changes during the wait, the previous provider instance is
/// disposed automatically by Riverpod's `autoDispose`, abandoning the stale
/// future — no explicit cancellation needed.
final cubeSearchResultsProvider =
    FutureProvider.autoDispose<List<CubeCatalogEntry>>((ref) async {
  final query = ref.watch(cubeSearchQueryProvider);

  if (query.trim().isEmpty) {
    return [];
  }

  // Debounce: wait 300 ms. If the user types another character during
  // this window, autoDispose tears down this provider instance and
  // creates a fresh one for the new query value.
  await Future.delayed(const Duration(milliseconds: 300));

  final repo = ref.read(cubeRepositoryProvider);
  return repo.search(query);
});

/// Fetches a single cube's full metadata by product ID.
final cubeDetailProvider = FutureProvider.autoDispose
    .family<CubeCatalogEntry, String>((ref, productId) async {
  final repo = ref.read(cubeRepositoryProvider);
  return repo.getByProductId(productId);
});
