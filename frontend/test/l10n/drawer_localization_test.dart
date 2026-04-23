import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:summa_vision_admin/core/app_bootstrap/app_bootstrap_provider.dart';
import 'package:summa_vision_admin/core/app_bootstrap/app_bootstrap_state.dart';
import 'package:summa_vision_admin/core/routing/app_drawer.dart';
import 'package:summa_vision_admin/core/routing/app_router.dart';
import 'package:summa_vision_admin/l10n/generated/app_localizations.dart';

class _FakeBootstrap extends AppBootstrapNotifier {
  _FakeBootstrap(this._languageCode);

  final String _languageCode;

  @override
  Future<AppBootstrapState> build() async {
    return AppBootstrapState(locale: Locale(_languageCode));
  }
}

Widget _drawerTestHarness({required String localeCode}) {
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

  return ProviderScope(
    overrides: [
      appBootstrapProvider.overrideWith(() => _FakeBootstrap(localeCode)),
    ],
    child: Consumer(
      builder: (context, ref, _) {
        final bootstrap = ref.watch(appBootstrapProvider);
        return MaterialApp.router(
          locale: bootstrap.valueOrNull?.locale ?? Locale(localeCode),
          supportedLocales: AppLocalizations.supportedLocales,
          localizationsDelegates: AppLocalizations.localizationsDelegates,
          routerConfig: router,
        );
      },
    ),
  );
}

void main() {
  group('AppDrawer localization', () {
    testWidgets('renders EN nav labels when locale is en', (tester) async {
      await tester.pumpWidget(_drawerTestHarness(localeCode: 'en'));
      await tester.pumpAndSettle();

      await tester.tap(find.byIcon(Icons.menu));
      await tester.pumpAndSettle();

      // EN-kept by policy: brand + product-line name (§3k Category A / D).
      expect(find.text('Summa Vision Admin'), findsOneWidget);
      expect(find.text('Brief Queue'), findsOneWidget);
      expect(find.text('Cubes'), findsOneWidget);
      expect(find.text('Jobs'), findsOneWidget);
      // EN-kept by policy: industry-standard abbreviation (§3k Category A).
      expect(find.text('KPI'), findsOneWidget);
    });

    testWidgets('renders RU nav labels when locale is ru', (tester) async {
      await tester.pumpWidget(_drawerTestHarness(localeCode: 'ru'));
      await tester.pumpAndSettle();

      await tester.tap(find.byIcon(Icons.menu));
      await tester.pumpAndSettle();

      // EN-kept by policy: brand + product-line name.
      expect(find.text('Summa Vision Admin'), findsOneWidget);
      // EN-kept by policy: industry-standard abbreviation.
      expect(find.text('KPI'), findsOneWidget);

      // Translated.
      expect(find.text('Очередь брифов'), findsOneWidget);
      expect(find.text('Кубы'), findsOneWidget);
      expect(find.text('Задачи'), findsOneWidget);

      // Denied: previous EN literals must NOT be present.
      expect(find.text('Brief Queue'), findsNothing);
      expect(find.text('Cubes'), findsNothing);
      expect(find.text('Jobs'), findsNothing);
    });
  });
}
