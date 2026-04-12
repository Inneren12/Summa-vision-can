import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../features/cubes/presentation/cube_detail_screen.dart';
import '../../features/cubes/presentation/cube_search_screen.dart';
import '../../features/data_preview/presentation/data_preview_screen.dart';
import '../../features/editor/presentation/editor_screen.dart';
import '../../features/graphics/presentation/chart_config_screen.dart';
import '../../features/graphics/presentation/preview_screen.dart';
import '../../features/kpi/presentation/kpi_screen.dart';
import '../../features/queue/presentation/queue_screen.dart';

/// Route path constants — single source of truth.
class AppRoutes {
  AppRoutes._();

  static const queue       = '/queue';
  static const editor      = '/editor/:briefId';
  static const preview     = '/preview/:taskId';
  static const cubeSearch   = '/cubes/search';
  static const cubeDetail   = '/cubes/:productId';
  static const dataPreview     = '/data/preview';
  static const graphicsConfig  = '/graphics/config';
  static const kpi             = '/kpi';
}

/// Riverpod provider for the [GoRouter] instance.
///
/// Injecting the router via Riverpod means any widget can call
/// `ref.read(routerProvider)` without needing a BuildContext, and
/// the router can be overridden in tests.
final routerProvider = Provider<GoRouter>((ref) {
  return GoRouter(
    initialLocation: AppRoutes.queue,
    debugLogDiagnostics: false,
    // Redirect unknown paths back to /queue
    redirect: (context, state) {
      final knownPrefixes = [
        '/queue',
        '/editor/',
        '/preview/',
        '/cubes/',
        '/data/',
        '/graphics/',
        '/kpi',
      ];
      final path = state.matchedLocation;

      // /cubes with no sub-path → redirect to /cubes/search
      if (path == '/cubes') return AppRoutes.cubeSearch;

      final isKnown = knownPrefixes.any((p) => path.startsWith(p));
      if (!isKnown && path != AppRoutes.queue) {
        return AppRoutes.queue;
      }
      return null; // no redirect needed
    },
    routes: [
      GoRoute(
        path: AppRoutes.queue,
        name: 'queue',
        builder: (context, state) => const QueueScreen(),
      ),
      GoRoute(
        path: AppRoutes.cubeSearch,
        name: 'cubeSearch',
        builder: (context, state) => const CubeSearchScreen(),
      ),
      GoRoute(
        path: AppRoutes.cubeDetail,
        name: 'cubeDetail',
        builder: (context, state) {
          final productId = state.pathParameters['productId'] ?? '';
          return CubeDetailScreen(productId: productId);
        },
      ),
      GoRoute(
        path: AppRoutes.dataPreview,
        name: 'dataPreview',
        builder: (context, state) {
          final key = state.uri.queryParameters['key'] ?? '';
          return DataPreviewScreen(storageKey: key);
        },
      ),
      GoRoute(
        path: AppRoutes.graphicsConfig,
        name: 'graphicsConfig',
        builder: (context, state) {
          final key = state.uri.queryParameters['key'] ?? '';
          final productId = state.uri.queryParameters['productId'];
          return ChartConfigScreen(
            storageKey: key,
            productId: productId,
          );
        },
      ),
      GoRoute(
        path: AppRoutes.kpi,
        name: 'kpi',
        builder: (context, state) => const KPIScreen(),
      ),
      GoRoute(
        path: AppRoutes.editor,
        name: 'editor',
        builder: (context, state) {
          final briefId = state.pathParameters['briefId'] ?? '';
          return EditorScreen(briefId: briefId);
        },
      ),
      GoRoute(
        path: AppRoutes.preview,
        name: 'preview',
        builder: (context, state) {
          final taskId = state.pathParameters['taskId'] ?? '';
          return PreviewScreen(taskId: taskId);
        },
      ),
    ],
  );
});
