import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:summa_vision_admin/core/routing/app_router.dart';
import 'package:summa_vision_admin/features/editor/presentation/editor_screen.dart';
import 'package:summa_vision_admin/features/graphics/domain/generation_notifier.dart';
import 'package:summa_vision_admin/features/graphics/domain/generation_state.dart';
import 'package:summa_vision_admin/features/graphics/presentation/preview_screen.dart';
import 'package:summa_vision_admin/features/queue/presentation/queue_screen.dart';
import 'package:summa_vision_admin/core/theme/app_theme.dart';

/// No-op notifier so PreviewScreen renders without calling real Dio.
class _NoOpGenerationNotifier extends GenerationNotifier {
  @override
  GenerationState build() => const GenerationState();

  @override
  Future<void> generate(int briefId) async {}
}

/// Builds a testable app with an overridable router.
Widget _buildApp(GoRouter router) {
  return ProviderScope(
    overrides: [
      routerProvider.overrideWithValue(router),
      generationNotifierProvider.overrideWith(() => _NoOpGenerationNotifier()),
    ],
    child: MaterialApp.router(
      theme: AppTheme.dark,
      routerConfig: router,
    ),
  );
}

/// Creates a fresh GoRouter from routerProvider for each test.
GoRouter _makeRouter() {
  final container = ProviderContainer();
  addTearDown(container.dispose);
  return container.read(routerProvider);
}

void main() {
  group('AppRoutes constants', () {
    test('queue route is /queue', () {
      expect(AppRoutes.queue, equals('/queue'));
    });

    test('editor route is /editor/:briefId', () {
      expect(AppRoutes.editor, equals('/editor/:briefId'));
    });

    test('preview route is /preview/:taskId', () {
      expect(AppRoutes.preview, equals('/preview/:taskId'));
    });
  });

  group('routerProvider', () {
    test('creates a GoRouter instance', () {
      final router = _makeRouter();
      expect(router, isA<GoRouter>());
    });

    testWidgets('initial location is /queue', (tester) async {
      final router = _makeRouter();
      await tester.pumpWidget(_buildApp(router));
      await tester.pumpAndSettle();
      expect(
        router.routerDelegate.currentConfiguration.fullPath,
        equals('/queue'),
      );
    });
  });

  group('Navigation — QueueScreen', () {
    testWidgets('initial route shows QueueScreen', (tester) async {
      final router = _makeRouter();
      await tester.pumpWidget(_buildApp(router));
      await tester.pumpAndSettle();

      expect(find.byType(QueueScreen), findsOneWidget);
      expect(find.text('Brief Queue'), findsOneWidget);
    });
  });

  group('Navigation — EditorScreen', () {
    testWidgets('navigating to /editor/42 shows EditorScreen with briefId', (tester) async {
      final router = _makeRouter();
      await tester.pumpWidget(_buildApp(router));
      await tester.pumpAndSettle();

      router.go('/editor/42');
      await tester.pumpAndSettle();

      expect(find.byType(EditorScreen), findsOneWidget);
      expect(find.textContaining('42'), findsWidgets);
    });

    testWidgets('editor extracts briefId from path parameter', (tester) async {
      final router = _makeRouter();
      await tester.pumpWidget(_buildApp(router));
      await tester.pumpAndSettle();

      router.go('/editor/99');
      await tester.pumpAndSettle();

      expect(find.textContaining('99'), findsWidgets);
    });
  });

  group('Navigation — PreviewScreen', () {
    testWidgets('navigating to /preview/task-abc shows PreviewScreen with taskId', (tester) async {
      final router = _makeRouter();
      await tester.pumpWidget(_buildApp(router));
      await tester.pumpAndSettle();

      router.go('/preview/task-abc');
      await tester.pumpAndSettle();

      expect(find.byType(PreviewScreen), findsOneWidget);
      expect(find.textContaining('Submitting'), findsOneWidget);
    });
  });

  group('Redirect — unknown paths', () {
    testWidgets('unknown path redirects to /queue', (tester) async {
      final router = GoRouter(
        initialLocation: '/nonexistent-path',
        redirect: (context, state) {
          final knownPrefixes = ['/queue', '/editor/', '/preview/'];
          final path = state.matchedLocation;
          final isKnown = knownPrefixes.any((p) => path.startsWith(p));
          if (!isKnown && path != AppRoutes.queue) return AppRoutes.queue;
          return null;
        },
        routes: [
          GoRoute(
            path: AppRoutes.queue,
            builder: (_, __) => const QueueScreen(),
          ),
          GoRoute(
            path: AppRoutes.editor,
            builder: (_, state) => EditorScreen(
              briefId: state.pathParameters['briefId'] ?? '',
            ),
          ),
          GoRoute(
            path: AppRoutes.preview,
            builder: (_, state) => PreviewScreen(
              taskId: state.pathParameters['taskId'] ?? '',
            ),
          ),
        ],
      );

      await tester.pumpWidget(_buildApp(router));
      await tester.pumpAndSettle();

      expect(find.byType(QueueScreen), findsOneWidget);
    });
  });

  group('Named navigation', () {
    testWidgets('goNamed editor navigates correctly', (tester) async {
      final router = _makeRouter();
      await tester.pumpWidget(_buildApp(router));
      await tester.pumpAndSettle();

      router.goNamed('editor', pathParameters: {'briefId': '7'});
      await tester.pumpAndSettle();

      expect(find.byType(EditorScreen), findsOneWidget);
      expect(find.textContaining('7'), findsWidgets);
    });

    testWidgets('goNamed preview navigates correctly', (tester) async {
      final router = _makeRouter();
      await tester.pumpWidget(_buildApp(router));
      await tester.pumpAndSettle();

      router.goNamed('preview', pathParameters: {'taskId': 'uuid-xyz'});
      await tester.pumpAndSettle();

      expect(find.byType(PreviewScreen), findsOneWidget);
      expect(find.textContaining('Generating Graphic'), findsOneWidget);
    });
  });
}
