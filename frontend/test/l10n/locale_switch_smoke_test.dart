import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:summa_vision_admin/core/app_bootstrap/app_bootstrap_provider.dart';
import 'package:summa_vision_admin/core/routing/app_drawer.dart';
import 'package:summa_vision_admin/core/routing/app_router.dart';
import 'package:summa_vision_admin/l10n/generated/app_localizations.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  group('Locale-switch smoke', () {
    testWidgets('EN → RU switches at least 3 visible strings', (tester) async {
      await tester.pumpWidget(
        const ProviderScope(
          child: _TestShell(),
        ),
      );
      await tester.pumpAndSettle();

      await _openDrawer(tester);

      expect(find.text('Language'), findsOneWidget);
      expect(find.text('Brief Queue'), findsOneWidget);
      expect(find.text('Jobs'), findsOneWidget);

      // Switching locale via the drawer switcher also dismisses the drawer
      // (standard Material behavior for tap inside Drawer).
      await tester.tap(find.text('Russian'));
      await tester.pumpAndSettle();

      // Reopen drawer to verify shell content now renders in RU.
      await _openDrawer(tester);

      expect(find.text('Язык'), findsOneWidget);
      expect(find.text('Очередь брифов'), findsOneWidget);
      expect(find.text('Задачи'), findsOneWidget);
    });

    testWidgets('locale change persists to SharedPreferences', (tester) async {
      await tester.pumpWidget(
        const ProviderScope(
          child: _TestShell(),
        ),
      );
      await tester.pumpAndSettle();

      await _openDrawer(tester);
      await tester.tap(find.text('Russian'));
      await tester.pumpAndSettle();

      final prefs = await SharedPreferences.getInstance();
      expect(prefs.getString(kLocaleStorageKey), 'ru');
    });
  });

  group('Bootstrap locale resolution', () {
    testWidgets('boots with persisted ru', (tester) async {
      SharedPreferences.setMockInitialValues({'selected_locale': 'ru'});

      await tester.pumpWidget(
        const ProviderScope(child: _TestShell()),
      );
      await tester.pumpAndSettle();

      await _openDrawer(tester);
      expect(find.text('Язык'), findsOneWidget);
    });

    testWidgets('boots with persisted en', (tester) async {
      SharedPreferences.setMockInitialValues({'selected_locale': 'en'});

      await tester.pumpWidget(
        const ProviderScope(child: _TestShell()),
      );
      await tester.pumpAndSettle();

      await _openDrawer(tester);
      expect(find.text('Language'), findsOneWidget);
    });

    testWidgets('unsupported persisted locale falls back to EN', (tester) async {
      SharedPreferences.setMockInitialValues({'selected_locale': 'fr'});

      await tester.pumpWidget(
        const ProviderScope(child: _TestShell()),
      );
      await tester.pumpAndSettle();

      await _openDrawer(tester);
      expect(find.text('Language'), findsOneWidget);
    });

    testWidgets('empty prefs + default device locale boots EN in test env', (
      tester,
    ) async {
      SharedPreferences.setMockInitialValues({});

      await tester.pumpWidget(
        const ProviderScope(child: _TestShell()),
      );
      await tester.pumpAndSettle();

      await _openDrawer(tester);
      expect(find.text('Language'), findsOneWidget);
    });
  });
}

Future<void> _openDrawer(WidgetTester tester) async {
  await tester.tap(find.byIcon(Icons.menu));
  await tester.pumpAndSettle();
}

class _TestShell extends ConsumerWidget {
  const _TestShell();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final bootstrap = ref.watch(appBootstrapProvider);
    final router = GoRouter(
      initialLocation: AppRoutes.queue,
      routes: [
        GoRoute(
          path: AppRoutes.queue,
          builder: (context, state) => Scaffold(
            drawer: const AppDrawer(),
            body: Builder(
              builder: (context) => IconButton(
                icon: const Icon(Icons.menu),
                onPressed: () => Scaffold.of(context).openDrawer(),
              ),
            ),
          ),
        ),
      ],
    );

    return MaterialApp.router(
      locale: bootstrap.when(
        data: (state) => state.locale,
        loading: () => const Locale('en'),
        error: (_, __) => const Locale('en'),
      ),
      supportedLocales: AppLocalizations.supportedLocales,
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      routerConfig: router,
    );
  }
}
