import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../features/editor/presentation/editor_screen.dart';
import '../../features/graphics/presentation/preview_screen.dart';
import '../../features/queue/presentation/queue_screen.dart';
import '../../features/jobs/presentation/jobs_dashboard_screen.dart';

/// Route path constants — single source of truth.
class AppRoutes {
  AppRoutes._();

  static const queue = '/queue';
  static const editor = '/editor/:briefId';
  static const preview = '/preview/:taskId';
  static const jobs = '/jobs';
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
      final knownPrefixes = ['/queue', '/editor/', '/preview/', '/jobs'];
      final path = state.matchedLocation;
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
      GoRoute(
        path: AppRoutes.jobs,
        name: 'jobs',
        builder: (context, state) => const JobsDashboardScreen(),
      ),
    ],
  );
});
