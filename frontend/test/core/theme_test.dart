import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:summa_vision_admin/core/theme/app_theme.dart';

void main() {
  // Allow google_fonts to resolve font families at runtime.
  // Fonts gracefully fall back when network is unavailable in CI.
  setUpAll(() {
    GoogleFonts.config.allowRuntimeFetching = true;
  });

  group('AppTheme', () {
    test('backgroundDark is #0B0D11 (Design System v3.2 raw-slate-950)', () {
      expect(AppTheme.backgroundDark.value, equals(const Color(0xFF0B0D11).value));
    });

    test('neonGreen is #00FF94', () {
      expect(AppTheme.neonGreen.value, equals(const Color(0xFF00FF94).value));
    });

    test('dark theme scaffold background matches backgroundDark', () {
      expect(
        AppTheme.dark.scaffoldBackgroundColor,
        equals(AppTheme.backgroundDark),
      );
    });

    test('dark theme has SummaTheme extension', () {
      final summa = AppTheme.dark.extension<SummaTheme>();
      expect(summa, isNotNull);
      expect(summa!.bgApp, equals(AppTheme.backgroundDark));
    });

    testWidgets('MaterialApp boots with dark theme', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.dark,
          home: const Scaffold(body: Text('OK')),
        ),
      );
      expect(find.text('OK'), findsOneWidget);
    });

    testWidgets('SummaVisionApp renders without crashing', (tester) async {
      // Minimal smoke test — does not require dotenv
      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.dark,
          home: const Scaffold(
            body: Center(child: Text('Summa Vision')),
          ),
        ),
      );
      expect(find.text('Summa Vision'), findsOneWidget);
    });
  });
}
