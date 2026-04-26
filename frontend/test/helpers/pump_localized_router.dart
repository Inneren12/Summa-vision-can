import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:summa_vision_admin/core/app_bootstrap/app_bootstrap_provider.dart';
import 'package:summa_vision_admin/core/theme/app_theme.dart';
import 'package:summa_vision_admin/l10n/generated/app_localizations.dart';

/// Pumps a localized app shell for locale-switch smoke tests.
///
/// Use [routerConfig] for tests that need navigation. Use [home] for
/// shell-level tests that isolate the language switcher.
///
/// Exactly one of [routerConfig] or [home] must be provided.
Future<void> pumpLocalizedRouter(
  WidgetTester tester, {
  RouterConfig<Object>? routerConfig,
  Widget? home,
  Locale initialLocale = const Locale('en'),
  List<Override> overrides = const [],
  Size surfaceSize = const Size(800, 600),
}) async {
  assert(
    (routerConfig == null) != (home == null),
    'Provide exactly one of routerConfig or home',
  );

  await tester.binding.setSurfaceSize(surfaceSize);
  addTearDown(() => tester.binding.setSurfaceSize(null));

  await tester.pumpWidget(
    ProviderScope(
      overrides: overrides,
      child: Consumer(
        builder: (context, ref, _) {
          final bootstrap = ref.watch(appBootstrapProvider);
          final locale = bootstrap.when(
            data: (state) => state.locale,
            loading: () => initialLocale,
            error: (_, __) => initialLocale,
          );

          if (routerConfig != null) {
            return MaterialApp.router(
              theme: AppTheme.dark,
              locale: locale,
              localizationsDelegates: AppLocalizations.localizationsDelegates,
              supportedLocales: AppLocalizations.supportedLocales,
              routerConfig: routerConfig,
            );
          }

          return MaterialApp(
            theme: AppTheme.dark,
            locale: locale,
            localizationsDelegates: AppLocalizations.localizationsDelegates,
            supportedLocales: AppLocalizations.supportedLocales,
            home: home!,
          );
        },
      ),
    ),
  );
  await tester.pumpAndSettle();
}

/// Returns AppLocalizations from a pumped widget tree.
///
/// Anchors on the first `Scaffold` in the tree because Scaffold sits BELOW
/// MaterialApp's internal Localizations widget and is present in every
/// locale-switch smoke. Anchoring on MaterialApp itself would return a
/// context above Localizations → AppLocalizations.of(context) returns null →
/// `!` crashes.
///
/// Diagnostic: if Scaffold is not found OR AppLocalizations is null,
/// surfaces a clear test failure rather than a NullCheckOperator crash.
AppLocalizations l10n(WidgetTester tester) {
  final scaffoldFinder = find.byType(Scaffold, skipOffstage: false);
  expect(
    scaffoldFinder,
    findsAtLeastNWidgets(1),
    reason: 'l10n(tester) requires a pumped localized widget tree '
        'containing at least one Scaffold. Did you forget '
        'pumpLocalizedRouter() before calling l10n()?',
  );

  final context = tester.element(scaffoldFinder.first);
  final localizations = AppLocalizations.of(context);
  expect(
    localizations,
    isNotNull,
    reason: 'AppLocalizations.of(context) returned null. The pumped tree '
        'is missing AppLocalizations.delegate or the helper anchored '
        'on a context above Localizations.',
  );
  return localizations!;
}

Future<void> switchLocaleVia(WidgetTester tester, String target) async {
  final switcher = find.byKey(
    ValueKey<String>('language-switcher-$target'),
    skipOffstage: false,
  );
  expect(
    switcher,
    findsOneWidget,
    reason: 'Language switcher target "$target" not found.',
  );

  await tester.tap(switcher);
  await tester.pumpAndSettle();
}
