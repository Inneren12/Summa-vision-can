import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/routing/app_drawer.dart';
import '../../../core/theme/app_theme.dart';
import '../application/cube_providers.dart';
import '../data/cube_repository.dart';
import 'widgets/cube_search_tile.dart';

class CubeSearchScreen extends ConsumerStatefulWidget {
  const CubeSearchScreen({super.key});

  @override
  ConsumerState<CubeSearchScreen> createState() => _CubeSearchScreenState();
}

class _CubeSearchScreenState extends ConsumerState<CubeSearchScreen> {
  final _controller = TextEditingController();

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final searchResults = ref.watch(cubeSearchResultsProvider);
    final query = ref.watch(cubeSearchQueryProvider);

    return Scaffold(
      drawer: const AppDrawer(),
      appBar: AppBar(
        title: const Text('Cube Search'),
        actions: [
          IconButton(
            icon: const Icon(Icons.sync),
            tooltip: 'Sync Catalog',
            onPressed: () => _triggerSync(context, ref),
          ),
        ],
      ),
      body: Column(
        children: [
          // Search bar
          Padding(
            padding: const EdgeInsets.all(16),
            child: TextField(
              controller: _controller,
              decoration: InputDecoration(
                hintText: 'Search StatCan cubes...',
                prefixIcon: const Icon(Icons.search),
                suffixIcon: query.isNotEmpty
                    ? IconButton(
                        icon: const Icon(Icons.clear),
                        onPressed: () {
                          _controller.clear();
                          ref.read(cubeSearchQueryProvider.notifier).state = '';
                        },
                      )
                    : null,
                filled: true,
                fillColor: AppTheme.surfaceDark,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(8),
                  borderSide: BorderSide.none,
                ),
              ),
              onChanged: (value) {
                ref.read(cubeSearchQueryProvider.notifier).state = value;
              },
            ),
          ),
          // Results
          Expanded(
            child: query.trim().isEmpty
                ? const Center(
                    child: Text(
                      'Enter a search term to find StatCan datasets',
                      style: TextStyle(color: AppTheme.textSecondary),
                    ),
                  )
                : searchResults.when(
                    loading: () => const Center(
                      child: CircularProgressIndicator(),
                    ),
                    error: (err, _) => Center(
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          const Icon(
                            Icons.error_outline,
                            color: AppTheme.errorRed,
                            size: 48,
                          ),
                          const SizedBox(height: 16),
                          Text(
                            'Failed to search cubes\n$err',
                            textAlign: TextAlign.center,
                            style: const TextStyle(
                              color: AppTheme.textSecondary,
                            ),
                          ),
                          const SizedBox(height: 16),
                          ElevatedButton(
                            onPressed: () =>
                                ref.invalidate(cubeSearchResultsProvider),
                            child: const Text('Retry'),
                          ),
                        ],
                      ),
                    ),
                    data: (cubes) => cubes.isEmpty
                        ? Center(
                            child: Text(
                              "No datasets found for '$query'. Try different keywords.",
                              textAlign: TextAlign.center,
                              style: const TextStyle(
                                color: AppTheme.textSecondary,
                              ),
                            ),
                          )
                        : ListView.separated(
                            padding: const EdgeInsets.symmetric(horizontal: 16),
                            itemCount: cubes.length,
                            separatorBuilder: (_, __) =>
                                const SizedBox(height: 8),
                            itemBuilder: (context, index) {
                              final entry = cubes[index];
                              return CubeSearchTile(
                                entry: entry,
                                onTap: () => context
                                    .push('/cubes/${entry.productId}'),
                              );
                            },
                          ),
                  ),
          ),
        ],
      ),
    );
  }

  Future<void> _triggerSync(BuildContext context, WidgetRef ref) async {
    try {
      final jobId = await ref.read(cubeRepositoryProvider).triggerSync();
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Catalog sync started (Job: $jobId)')),
        );
      }
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Sync failed: $e'),
            backgroundColor: AppTheme.errorRed,
          ),
        );
      }
    }
  }
}
