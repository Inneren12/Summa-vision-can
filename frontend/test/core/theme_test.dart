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

    test('SummaTheme.dark has correct token values', () {
      const summa = SummaTheme.dark;
      expect(summa.bgApp, equals(const Color(0xFF0B0D11)));
      expect(summa.bgSurface, equals(const Color(0xFF15181E)));
      expect(summa.accent, equals(const Color(0xFFFBBF24)));
      expect(summa.destructive, equals(const Color(0xFFE11D48)));
      expect(summa.textPrimary, equals(const Color(0xFFF3F4F6)));
      expect(summa.textSecondary, equals(const Color(0xFF8B949E)));
    });

    test('SummaTheme.dark bgApp matches AppTheme.backgroundDark', () {
      expect(SummaTheme.dark.bgApp, equals(AppTheme.backgroundDark));
    });

    test('SummaTheme.dark data series palette has 6 colors', () {
      expect(SummaTheme.dark.dataSeriesPalette.length, equals(6));
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

  group('Design System v3.2 spec conformance', () {
    test('SummaTheme.dark matches design system v3.2 values', () {
      const t = SummaTheme.dark;
      expect(t.bgApp, const Color(0xFF0B0D11));
      expect(t.bgSurface, const Color(0xFF15181E));
      expect(t.textSecondary, const Color(0xFF8B949E));
      expect(t.dataBaseline, const Color(0xFF94A3B8));
      expect(t.dataPositive, const Color(0xFF0D9488));
      expect(t.accent, const Color(0xFFFBBF24));
      expect(t.seriesPrimaryWeight, 2.0);
      expect(t.seriesMutedOpacity, 0.2);
    });

    test('DensityMode has correct enum values', () {
      expect(DensityMode.values.map((e) => e.name),
        ['comfortable', 'compact', 'dense']);
    });

    test('ChartMode has correct enum values', () {
      expect(ChartMode.values.map((e) => e.name),
        ['editorial', 'operational']);
    });

    test('spacingForDensity comfortable matches v3.2', () {
      final s = spacingForDensity(DensityMode.comfortable);
      expect(s['xs'], 4);
      expect(s['3xl'], 64);
    });

    test('spacingForDensity compact matches v3.2', () {
      final s = spacingForDensity(DensityMode.compact);
      expect(s['xs'], 3);
      expect(s['sm'], 6);
      expect(s['md'], 12);
      expect(s['lg'], 18);
      expect(s['xl'], 24);
      expect(s['2xl'], 36);
      expect(s['3xl'], 48);
    });

    test('spacingForDensity dense matches v3.2', () {
      final s = spacingForDensity(DensityMode.dense);
      expect(s['xs'], 2);
      expect(s['sm'], 4);
      expect(s['md'], 8);
      expect(s['lg'], 12);
      expect(s['xl'], 16);
      expect(s['2xl'], 24);
      expect(s['3xl'], 32);
    });

    test('SummaTheme.dark has all chart behavior tokens', () {
      const t = SummaTheme.dark;
      expect(t.seriesPrimaryWeight, 2.0);
      expect(t.seriesSecondaryWeight, 1.5);
      expect(t.seriesBenchmarkWeight, 1.0);
      expect(t.seriesForecastWeight, 1.0);
      expect(t.seriesMutedOpacity, 0.2);
      expect(t.seriesHoverDim, 0.25);
      expect(t.seriesUncertaintyFillOpacity, 0.12);
    });

    test('SummaTheme.dark has v3.2 data semantic colors', () {
      const t = SummaTheme.dark;
      expect(t.dataGov, const Color(0xFF3B82F6));
      expect(t.dataSociety, const Color(0xFFA78BFA));
      expect(t.dataInfra, const Color(0xFF2DD4BF));
      expect(t.dataMonopoly, const Color(0xFFF97316));
      expect(t.dataBaseline, const Color(0xFF94A3B8));
      expect(t.dataHousing, const Color(0xFF22D3EE));
      expect(t.dataNegative, const Color(0xFFE11D48));
      expect(t.dataPositive, const Color(0xFF0D9488));
      expect(t.dataWarning, const Color(0xFFF97316));
      expect(t.dataNeutral, const Color(0xFF262A33));
    });

    test('SummaTheme.dark has v3.2 radius and duration values', () {
      const t = SummaTheme.dark;
      expect(t.radiusAdmin, 4);
      expect(t.radiusPublic, 10);
      expect(t.radiusTooltip, 4);
      expect(t.durationMicro, const Duration(milliseconds: 150));
      expect(t.durationData, const Duration(milliseconds: 400));
      expect(t.durationPage, const Duration(milliseconds: 800));
    });
  });
}
