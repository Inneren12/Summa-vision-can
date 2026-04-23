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

      await tester.tap(find.byIcon(Icons.menu));
      await tester.pumpAndSettle();

      expect(find.text('Language'), findsOneWidget);
      expect(find.text('Brief Queue'), findsOneWidget);
      expect(find.text('Jobs'), findsOneWidget);

      await tester.tap(find.text('Russian'));
      await tester.pumpAndSettle();

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

      await tester.tap(find.byIcon(Icons.menu));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Russian'));
      await tester.pumpAndSettle();

      final prefs = await SharedPreferences.getInstance();
      expect(prefs.getString(kLocaleStorageKey), 'ru');
    });
  });
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
      locale: bootstrap.valueOrNull?.locale ?? const Locale('en'),
      supportedLocales: AppLocalizations.supportedLocales,
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      routerConfig: router,
    );
  }
}
