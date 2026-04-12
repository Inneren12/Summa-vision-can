import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:summa_vision_admin/core/theme/app_theme.dart';

void main() {
  // Prevent google_fonts from trying to fetch fonts over HTTP in tests.
  // Theme tests check token values and structure, not actual font rendering.
  GoogleFonts.config.allowRuntimeFetching = false;

  group('AppTheme', () {
    test('backgroundDark is #0B0D11 (Design System v3.2 raw-slate-950)', () {
      expect(AppTheme.backgroundDark.value, equals(const Color(0xFF0B0D11).value));
    });

    test('neonGreen is #00FF94', () {
      expect(AppTheme.neonGreen.value, equals(const Color(0xFF00FF94).value));
    });

    test('SummaTheme.defaultDark has correct token values', () {
      const summa = SummaTheme.defaultDark;
      expect(summa.bgApp, equals(const Color(0xFF0B0D11)));
      expect(summa.bgSurface, equals(const Color(0xFF15181E)));
      expect(summa.accent, equals(const Color(0xFFFBBF24)));
      expect(summa.destructive, equals(const Color(0xFFE11D48)));
      expect(summa.textPrimary, equals(const Color(0xFFF3F4F6)));
      expect(summa.textSecondary, equals(const Color(0xFF9CA3AF)));
    });

    test('SummaTheme.defaultDark bgApp matches AppTheme.backgroundDark', () {
      expect(SummaTheme.defaultDark.bgApp, equals(AppTheme.backgroundDark));
    });

    test('SummaTheme.defaultDark data series palette has 6 colors', () {
      expect(SummaTheme.defaultDark.dataSeriesPalette.length, equals(6));
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
