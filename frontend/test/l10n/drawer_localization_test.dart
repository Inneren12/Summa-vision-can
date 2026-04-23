import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:summa_vision_admin/l10n/generated/app_localizations.dart';

void main() {
  group('Drawer localization', () {
    testWidgets('renders EN nav labels when locale is en', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          locale: const Locale('en'),
          supportedLocales: const [Locale('en'), Locale('ru')],
          localizationsDelegates: const [
            AppLocalizations.delegate,
            GlobalMaterialLocalizations.delegate,
            GlobalWidgetsLocalizations.delegate,
            GlobalCupertinoLocalizations.delegate,
          ],
          home: const Scaffold(body: SizedBox.shrink()),
        ),
      );

      final context = tester.element(find.byType(Scaffold));
      final loc = AppLocalizations.of(context)!;
      expect(loc.appTitle, 'Summa Vision');
      expect(loc.navQueue, 'Brief Queue');
      expect(loc.navKpi, 'KPI');
    });

    testWidgets('renders RU nav labels when locale is ru', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          locale: const Locale('ru'),
          supportedLocales: const [Locale('en'), Locale('ru')],
          localizationsDelegates: const [
            AppLocalizations.delegate,
            GlobalMaterialLocalizations.delegate,
            GlobalWidgetsLocalizations.delegate,
            GlobalCupertinoLocalizations.delegate,
          ],
          home: const Scaffold(body: SizedBox.shrink()),
        ),
      );

      final context = tester.element(find.byType(Scaffold));
      final loc = AppLocalizations.of(context)!;
      expect(loc.appTitle, 'Summa Vision');
      expect(loc.navQueue, 'Очередь брифов');
      expect(loc.navKpi, 'KPI');
    });
  });
}
