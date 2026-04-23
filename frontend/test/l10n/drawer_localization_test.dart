import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:summa_vision_admin/core/routing/app_drawer.dart';
import 'package:summa_vision_admin/core/routing/app_router.dart';
import 'package:summa_vision_admin/l10n/generated/app_localizations.dart';

Widget _wrap({required Locale locale}) {
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
    child: MaterialApp.router(
      locale: locale,
      supportedLocales: AppLocalizations.supportedLocales,
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      routerConfig: router,
    ),
  );
}

void main() {
  group('AppDrawer localization', () {
    testWidgets('renders EN nav labels when locale is en', (tester) async {
      await tester.pumpWidget(_wrap(locale: const Locale('en')));

      await tester.tap(find.byIcon(Icons.menu));
      await tester.pumpAndSettle();

      expect(find.text('Summa Vision Admin'), findsOneWidget);
      expect(find.text('Brief Queue'), findsOneWidget);
      expect(find.text('Cubes'), findsOneWidget);
      expect(find.text('Jobs'), findsOneWidget);
      expect(find.text('KPI'), findsOneWidget);
    });

    testWidgets('renders RU nav labels when locale is ru', (tester) async {
      await tester.pumpWidget(_wrap(locale: const Locale('ru')));

      await tester.tap(find.byIcon(Icons.menu));
      await tester.pumpAndSettle();

      expect(find.text('Summa Vision Admin'), findsOneWidget);
      expect(find.text('KPI'), findsOneWidget);
      expect(find.text('Очередь брифов'), findsOneWidget);
      expect(find.text('Кубы'), findsOneWidget);
      expect(find.text('Задачи'), findsOneWidget);
      expect(find.text('Brief Queue'), findsNothing);
      expect(find.text('Cubes'), findsNothing);
      expect(find.text('Jobs'), findsNothing);
    });
  });
}
