import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:summa_vision_admin/core/app_bootstrap/app_bootstrap_provider.dart';
import 'package:summa_vision_admin/core/routing/app_drawer.dart';

import '../helpers/pump_localized_router.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  group('Locale-switch smoke', () {
    testWidgets('EN → RU switches at least 3 visible strings', (tester) async {
      await _pumpShell(tester);

      await _openDrawer(tester);

      final enLanguage = l10n(tester).languageLabel;
      final enQueue = l10n(tester).navQueue;
      final enJobs = l10n(tester).navJobs;

      expect(find.text(enLanguage, skipOffstage: false), findsOneWidget);
      expect(find.text(enQueue, skipOffstage: false), findsOneWidget);
      expect(find.text(enJobs, skipOffstage: false), findsOneWidget);

      await switchLocaleVia(tester, 'ru');

      await _openDrawer(tester);

      expect(
        find.text(l10n(tester).languageLabel, skipOffstage: false),
        findsOneWidget,
      );
      expect(
        find.text(l10n(tester).navQueue, skipOffstage: false),
        findsOneWidget,
      );
      expect(
        find.text(l10n(tester).navJobs, skipOffstage: false),
        findsOneWidget,
      );

      expect(find.text(enLanguage, skipOffstage: false), findsNothing);
      expect(find.text(enQueue, skipOffstage: false), findsNothing);
      expect(find.text(enJobs, skipOffstage: false), findsNothing);
    });

    testWidgets('locale change persists to SharedPreferences', (tester) async {
      await _pumpShell(tester);

      await _openDrawer(tester);
      await switchLocaleVia(tester, 'ru');

      final prefs = await SharedPreferences.getInstance();
      expect(prefs.getString(kLocaleStorageKey), 'ru');
    });
  });

  // NOTE: Tests in this group MUST assert against fixed EN/RU literals,
  // not against l10n(tester).<key>. Using the live l10n helper here would
  // be tautological — it derives expected text from whatever locale the
  // app actually booted, so the assertion would always pass regardless of
  // whether bootstrap resolved the intended locale. Hardcoded literals are
  // intentional in this group and should NOT be "fixed" by future
  // refactors. See DEBT-032 FR2 for context.
  group('Bootstrap locale resolution', () {
    testWidgets('boots with persisted ru', (tester) async {
      SharedPreferences.setMockInitialValues({'selected_locale': 'ru'});

      await _pumpShell(tester);

      await _openDrawer(tester);
      // Bootstrap with persisted 'ru' must render RU label, not EN.
      // Hardcoded RU literal is intentional — using l10n(tester) here would
      // be tautological (it would derive expected text from actual locale,
      // always passing regardless of correctness).
      expect(
        find.text('Язык', skipOffstage: false),
        findsOneWidget,
        reason: 'Persisted ru should boot in RU; saw non-RU label',
      );
    });

    testWidgets('boots with persisted en', (tester) async {
      SharedPreferences.setMockInitialValues({'selected_locale': 'en'});

      await _pumpShell(tester);

      await _openDrawer(tester);
      expect(
        find.text('Language', skipOffstage: false),
        findsOneWidget,
        reason: 'Persisted en should boot in EN and render EN language label',
      );
    });

    testWidgets('unsupported persisted locale falls back to EN', (tester) async {
      SharedPreferences.setMockInitialValues({'selected_locale': 'fr'});

      await _pumpShell(tester);

      await _openDrawer(tester);
      expect(
        find.text('Language', skipOffstage: false),
        findsOneWidget,
        reason: 'Unsupported persisted locale must fall back to EN at bootstrap',
      );
    });

    testWidgets('empty prefs + default device locale boots EN in test env', (
      tester,
    ) async {
      SharedPreferences.setMockInitialValues({});

      await _pumpShell(tester);

      await _openDrawer(tester);
      expect(
        find.text('Language', skipOffstage: false),
        findsOneWidget,
        reason: 'Empty prefs in test env should bootstrap with EN locale',
      );
    });
  });
}

Future<void> _pumpShell(WidgetTester tester) async {
  final router = GoRouter(
    routes: [
      GoRoute(
        path: '/',
        builder: (context, state) => const Scaffold(
          drawer: AppDrawer(),
          body: _DrawerLauncher(),
        ),
      ),
    ],
  );

  await pumpLocalizedRouter(
    tester,
    routerConfig: router,
  );
}

Future<void> _openDrawer(WidgetTester tester) async {
  await tester.tap(find.byIcon(Icons.menu));
  await tester.pumpAndSettle();
}

class _DrawerLauncher extends StatelessWidget {
  const _DrawerLauncher();

  @override
  Widget build(BuildContext context) {
    return Builder(
      builder: (context) => IconButton(
        icon: const Icon(Icons.menu),
        onPressed: () => Scaffold.of(context).openDrawer(),
      ),
    );
  }
}
