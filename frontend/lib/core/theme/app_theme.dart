import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

// ═══════════════════════════════════════════════════════════
// SUMMA VISION — Design System v3.2 Flutter Token Mapping
// (БЛОК 17 — exact spec values)
// ═══════════════════════════════════════════════════════════

/// Density modes for spacing configuration (v3.2 БЛОК 17).
enum DensityMode { comfortable, compact, dense }

/// Chart display modes (v3.2 БЛОК 17).
enum ChartMode { editorial, operational }

/// Design system theme extension for Summa Vision.
///
/// Access via `Theme.of(context).extension<SummaTheme>()!`.
class SummaTheme extends ThemeExtension<SummaTheme> {
  const SummaTheme({
    // Layer 1 — Raw Palette
    required this.rawSlate950,
    required this.rawSlate900,
    required this.rawSlate800,
    required this.rawSlate700,
    required this.rawSlate600,
    required this.rawSlate500,
    required this.rawSlate400,
    required this.rawSlate300,
    required this.rawSlate200,
    required this.rawSlate100,
    required this.rawSlate50,
    required this.rawAmber400,
    required this.rawAmber500,
    required this.rawAmber600,
    required this.rawRed500,
    required this.rawBlue500,
    required this.rawPurple400,
    required this.rawTeal400,
    required this.rawOrange500,
    required this.rawEmerald500,
    required this.rawYellow500,
    required this.rawCyan400,
    // Layer 2 — Semantic
    required this.bgApp,
    required this.bgSurface,
    required this.bgSurfaceHover,
    required this.bgSurfaceActive,
    required this.borderDefault,
    required this.borderSubtle,
    required this.borderFocus,
    required this.textPrimary,
    required this.textSecondary,
    required this.textMuted,
    required this.textInverse,
    required this.accent,
    required this.accentHover,
    required this.accentMuted,
    required this.destructive,
    // Layer 3 — Component
    required this.cardBg,
    required this.cardBorder,
    required this.tooltipBg,
    required this.tooltipText,
    required this.btnPrimaryBg,
    required this.btnPrimaryText,
    // Layer 4 — Data Semantic
    required this.dataGov,
    required this.dataSociety,
    required this.dataInfra,
    required this.dataMonopoly,
    required this.dataBaseline,
    required this.dataHousing,
    required this.dataNegative,
    required this.dataPositive,
    required this.dataWarning,
    required this.dataNeutral,
    // Spacing
    required this.spaceXs,
    required this.spaceSm,
    required this.spaceMd,
    required this.spaceLg,
    required this.spaceXl,
    required this.space2xl,
    required this.space3xl,
    // Radii
    required this.radiusAdmin,
    required this.radiusPublic,
    required this.radiusButton,
    required this.radiusTooltip,
    // Motion
    required this.durationMicro,
    required this.durationData,
    required this.durationPage,
    // Chart & Density
    required this.chartMode,
    required this.densityMode,
    // Chart behavior tokens (v3.2 БЛОК 17)
    required this.seriesPrimaryWeight,
    required this.seriesSecondaryWeight,
    required this.seriesBenchmarkWeight,
    required this.seriesForecastWeight,
    required this.seriesMutedOpacity,
    required this.seriesHoverDim,
    required this.seriesUncertaintyFillOpacity,
  });

  // ─── Layer 1 — Raw Palette ──────────────────────────────
  final Color rawSlate950;
  final Color rawSlate900;
  final Color rawSlate800;
  final Color rawSlate700;
  final Color rawSlate600;
  final Color rawSlate500;
  final Color rawSlate400;
  final Color rawSlate300;
  final Color rawSlate200;
  final Color rawSlate100;
  final Color rawSlate50;
  final Color rawAmber400;
  final Color rawAmber500;
  final Color rawAmber600;
  final Color rawRed500;
  final Color rawBlue500;
  final Color rawPurple400;
  final Color rawTeal400;
  final Color rawOrange500;
  final Color rawEmerald500;
  final Color rawYellow500;
  final Color rawCyan400;

  // ─── Layer 2 — Semantic ─────────────────────────────────
  final Color bgApp;
  final Color bgSurface;
  final Color bgSurfaceHover;
  final Color bgSurfaceActive;
  final Color borderDefault;
  final Color borderSubtle;
  final Color borderFocus;
  final Color textPrimary;
  final Color textSecondary;
  final Color textMuted;
  final Color textInverse;
  final Color accent;
  final Color accentHover;
  final Color accentMuted;
  final Color destructive;

  // ─── Layer 3 — Component ────────────────────────────────
  final Color cardBg;
  final Color cardBorder;
  final Color tooltipBg;
  final Color tooltipText;
  final Color btnPrimaryBg;
  final Color btnPrimaryText;

  // ─── Layer 4 — Data Semantic ────────────────────────────
  final Color dataGov;
  final Color dataSociety;
  final Color dataInfra;
  final Color dataMonopoly;
  final Color dataBaseline;
  final Color dataHousing;
  final Color dataNegative;
  final Color dataPositive;
  final Color dataWarning;
  final Color dataNeutral;

  // ─── Spacing ────────────────────────────────────────────
  final double spaceXs;
  final double spaceSm;
  final double spaceMd;
  final double spaceLg;
  final double spaceXl;
  final double space2xl;
  final double space3xl;

  // ─── Radii ──────────────────────────────────────────────
  final double radiusAdmin;
  final double radiusPublic;
  final double radiusButton;
  final double radiusTooltip;

  // ─── Motion ─────────────────────────────────────────────
  final Duration durationMicro;
  final Duration durationData;
  final Duration durationPage;

  // ─── Chart & Density ────────────────────────────────────
  final ChartMode chartMode;
  final DensityMode densityMode;

  // ─── Chart Behavior Tokens (v3.2 БЛОК 17) ──────────────
  final double seriesPrimaryWeight;
  final double seriesSecondaryWeight;
  final double seriesBenchmarkWeight;
  final double seriesForecastWeight;
  final double seriesMutedOpacity;
  final double seriesHoverDim;
  final double seriesUncertaintyFillOpacity;

  /// Data series palette for charts (ordered).
  List<Color> get dataSeriesPalette => [
        dataGov,
        dataSociety,
        dataInfra,
        dataMonopoly,
        dataBaseline,
        dataHousing,
      ];

  /// Default dark theme instance (v3.2 БЛОК 17 values).
  static const dark = SummaTheme(
    // Layer 1
    rawSlate950: Color(0xFF0B0D11),
    rawSlate900: Color(0xFF15181E),
    rawSlate800: Color(0xFF1C1F26),
    rawSlate700: Color(0xFF262A33),
    rawSlate600: Color(0xFF5C6370),
    rawSlate500: Color(0xFF6B7280),
    rawSlate400: Color(0xFF9CA3AF),
    rawSlate300: Color(0xFFD1D5DB),
    rawSlate200: Color(0xFFE5E7EB),
    rawSlate100: Color(0xFFF3F4F6),
    rawSlate50: Color(0xFFF9FAFB),
    rawAmber400: Color(0xFFFBBF24),
    rawAmber500: Color(0xFFF59E0B),
    rawAmber600: Color(0xFFD97706),
    rawRed500: Color(0xFFE11D48),
    rawBlue500: Color(0xFF3B82F6),
    rawPurple400: Color(0xFFA78BFA),
    rawTeal400: Color(0xFF2DD4BF),
    rawOrange500: Color(0xFFF97316),
    rawEmerald500: Color(0xFF10B981),
    rawYellow500: Color(0xFFEAB308),
    rawCyan400: Color(0xFF22D3EE),
    // Layer 2 — exact v3.2 values
    bgApp: Color(0xFF0B0D11),
    bgSurface: Color(0xFF15181E),
    bgSurfaceHover: Color(0xFF1C1F26),
    bgSurfaceActive: Color(0xFF262A33),
    borderDefault: Color(0xFF262A33),
    borderSubtle: Color(0xFF1C1F26),
    borderFocus: Color(0xFFFBBF24),
    textPrimary: Color(0xFFF3F4F6),
    textSecondary: Color(0xFF8B949E),
    textMuted: Color(0xFF5C6370),
    textInverse: Color(0xFF0B0D11),
    accent: Color(0xFFFBBF24),
    accentHover: Color(0xFFF59E0B),
    accentMuted: Color(0x26FBBF24), // 15% opacity
    destructive: Color(0xFFE11D48),
    // Layer 3
    cardBg: Color(0xFF15181E),
    cardBorder: Color(0xFF262A33),
    tooltipBg: Color(0xFF1C1F26),
    tooltipText: Color(0xFFF3F4F6),
    btnPrimaryBg: Color(0xFFFBBF24),
    btnPrimaryText: Color(0xFF0B0D11),
    // Layer 4 — exact v3.2 values
    dataGov: Color(0xFF3B82F6),
    dataSociety: Color(0xFFA78BFA),
    dataInfra: Color(0xFF2DD4BF),
    dataMonopoly: Color(0xFFF97316),
    dataBaseline: Color(0xFF94A3B8),
    dataHousing: Color(0xFF22D3EE),
    dataNegative: Color(0xFFE11D48),
    dataPositive: Color(0xFF0D9488),
    dataWarning: Color(0xFFF97316),
    dataNeutral: Color(0xFF262A33),
    // Spacing (comfortable defaults)
    spaceXs: 4,
    spaceSm: 8,
    spaceMd: 16,
    spaceLg: 24,
    spaceXl: 32,
    space2xl: 48,
    space3xl: 64,
    // Radii — v3.2 values
    radiusAdmin: 4,
    radiusPublic: 10,
    radiusButton: 8,
    radiusTooltip: 4,
    // Motion — v3.2 values
    durationMicro: Duration(milliseconds: 150),
    durationData: Duration(milliseconds: 400),
    durationPage: Duration(milliseconds: 800),
    // Chart & Density
    chartMode: ChartMode.editorial,
    densityMode: DensityMode.comfortable,
    // Chart behavior tokens — v3.2 БЛОК 17
    seriesPrimaryWeight: 2.0,
    seriesSecondaryWeight: 1.5,
    seriesBenchmarkWeight: 1.0,
    seriesForecastWeight: 1.0,
    seriesMutedOpacity: 0.2,
    seriesHoverDim: 0.25,
    seriesUncertaintyFillOpacity: 0.12,
  );

  @override
  SummaTheme copyWith({
    Color? rawSlate950,
    Color? rawSlate900,
    Color? rawSlate800,
    Color? rawSlate700,
    Color? rawSlate600,
    Color? rawSlate500,
    Color? rawSlate400,
    Color? rawSlate300,
    Color? rawSlate200,
    Color? rawSlate100,
    Color? rawSlate50,
    Color? rawAmber400,
    Color? rawAmber500,
    Color? rawAmber600,
    Color? rawRed500,
    Color? rawBlue500,
    Color? rawPurple400,
    Color? rawTeal400,
    Color? rawOrange500,
    Color? rawEmerald500,
    Color? rawYellow500,
    Color? rawCyan400,
    Color? bgApp,
    Color? bgSurface,
    Color? bgSurfaceHover,
    Color? bgSurfaceActive,
    Color? borderDefault,
    Color? borderSubtle,
    Color? borderFocus,
    Color? textPrimary,
    Color? textSecondary,
    Color? textMuted,
    Color? textInverse,
    Color? accent,
    Color? accentHover,
    Color? accentMuted,
    Color? destructive,
    Color? cardBg,
    Color? cardBorder,
    Color? tooltipBg,
    Color? tooltipText,
    Color? btnPrimaryBg,
    Color? btnPrimaryText,
    Color? dataGov,
    Color? dataSociety,
    Color? dataInfra,
    Color? dataMonopoly,
    Color? dataBaseline,
    Color? dataHousing,
    Color? dataNegative,
    Color? dataPositive,
    Color? dataWarning,
    Color? dataNeutral,
    double? spaceXs,
    double? spaceSm,
    double? spaceMd,
    double? spaceLg,
    double? spaceXl,
    double? space2xl,
    double? space3xl,
    double? radiusAdmin,
    double? radiusPublic,
    double? radiusButton,
    double? radiusTooltip,
    Duration? durationMicro,
    Duration? durationData,
    Duration? durationPage,
    ChartMode? chartMode,
    DensityMode? densityMode,
    double? seriesPrimaryWeight,
    double? seriesSecondaryWeight,
    double? seriesBenchmarkWeight,
    double? seriesForecastWeight,
    double? seriesMutedOpacity,
    double? seriesHoverDim,
    double? seriesUncertaintyFillOpacity,
  }) {
    return SummaTheme(
      rawSlate950: rawSlate950 ?? this.rawSlate950,
      rawSlate900: rawSlate900 ?? this.rawSlate900,
      rawSlate800: rawSlate800 ?? this.rawSlate800,
      rawSlate700: rawSlate700 ?? this.rawSlate700,
      rawSlate600: rawSlate600 ?? this.rawSlate600,
      rawSlate500: rawSlate500 ?? this.rawSlate500,
      rawSlate400: rawSlate400 ?? this.rawSlate400,
      rawSlate300: rawSlate300 ?? this.rawSlate300,
      rawSlate200: rawSlate200 ?? this.rawSlate200,
      rawSlate100: rawSlate100 ?? this.rawSlate100,
      rawSlate50: rawSlate50 ?? this.rawSlate50,
      rawAmber400: rawAmber400 ?? this.rawAmber400,
      rawAmber500: rawAmber500 ?? this.rawAmber500,
      rawAmber600: rawAmber600 ?? this.rawAmber600,
      rawRed500: rawRed500 ?? this.rawRed500,
      rawBlue500: rawBlue500 ?? this.rawBlue500,
      rawPurple400: rawPurple400 ?? this.rawPurple400,
      rawTeal400: rawTeal400 ?? this.rawTeal400,
      rawOrange500: rawOrange500 ?? this.rawOrange500,
      rawEmerald500: rawEmerald500 ?? this.rawEmerald500,
      rawYellow500: rawYellow500 ?? this.rawYellow500,
      rawCyan400: rawCyan400 ?? this.rawCyan400,
      bgApp: bgApp ?? this.bgApp,
      bgSurface: bgSurface ?? this.bgSurface,
      bgSurfaceHover: bgSurfaceHover ?? this.bgSurfaceHover,
      bgSurfaceActive: bgSurfaceActive ?? this.bgSurfaceActive,
      borderDefault: borderDefault ?? this.borderDefault,
      borderSubtle: borderSubtle ?? this.borderSubtle,
      borderFocus: borderFocus ?? this.borderFocus,
      textPrimary: textPrimary ?? this.textPrimary,
      textSecondary: textSecondary ?? this.textSecondary,
      textMuted: textMuted ?? this.textMuted,
      textInverse: textInverse ?? this.textInverse,
      accent: accent ?? this.accent,
      accentHover: accentHover ?? this.accentHover,
      accentMuted: accentMuted ?? this.accentMuted,
      destructive: destructive ?? this.destructive,
      cardBg: cardBg ?? this.cardBg,
      cardBorder: cardBorder ?? this.cardBorder,
      tooltipBg: tooltipBg ?? this.tooltipBg,
      tooltipText: tooltipText ?? this.tooltipText,
      btnPrimaryBg: btnPrimaryBg ?? this.btnPrimaryBg,
      btnPrimaryText: btnPrimaryText ?? this.btnPrimaryText,
      dataGov: dataGov ?? this.dataGov,
      dataSociety: dataSociety ?? this.dataSociety,
      dataInfra: dataInfra ?? this.dataInfra,
      dataMonopoly: dataMonopoly ?? this.dataMonopoly,
      dataBaseline: dataBaseline ?? this.dataBaseline,
      dataHousing: dataHousing ?? this.dataHousing,
      dataNegative: dataNegative ?? this.dataNegative,
      dataPositive: dataPositive ?? this.dataPositive,
      dataWarning: dataWarning ?? this.dataWarning,
      dataNeutral: dataNeutral ?? this.dataNeutral,
      spaceXs: spaceXs ?? this.spaceXs,
      spaceSm: spaceSm ?? this.spaceSm,
      spaceMd: spaceMd ?? this.spaceMd,
      spaceLg: spaceLg ?? this.spaceLg,
      spaceXl: spaceXl ?? this.spaceXl,
      space2xl: space2xl ?? this.space2xl,
      space3xl: space3xl ?? this.space3xl,
      radiusAdmin: radiusAdmin ?? this.radiusAdmin,
      radiusPublic: radiusPublic ?? this.radiusPublic,
      radiusButton: radiusButton ?? this.radiusButton,
      radiusTooltip: radiusTooltip ?? this.radiusTooltip,
      durationMicro: durationMicro ?? this.durationMicro,
      durationData: durationData ?? this.durationData,
      durationPage: durationPage ?? this.durationPage,
      chartMode: chartMode ?? this.chartMode,
      densityMode: densityMode ?? this.densityMode,
      seriesPrimaryWeight: seriesPrimaryWeight ?? this.seriesPrimaryWeight,
      seriesSecondaryWeight: seriesSecondaryWeight ?? this.seriesSecondaryWeight,
      seriesBenchmarkWeight: seriesBenchmarkWeight ?? this.seriesBenchmarkWeight,
      seriesForecastWeight: seriesForecastWeight ?? this.seriesForecastWeight,
      seriesMutedOpacity: seriesMutedOpacity ?? this.seriesMutedOpacity,
      seriesHoverDim: seriesHoverDim ?? this.seriesHoverDim,
      seriesUncertaintyFillOpacity: seriesUncertaintyFillOpacity ?? this.seriesUncertaintyFillOpacity,
    );
  }

  @override
  SummaTheme lerp(SummaTheme? other, double t) {
    if (other is! SummaTheme) return this;
    return SummaTheme(
      rawSlate950: Color.lerp(rawSlate950, other.rawSlate950, t)!,
      rawSlate900: Color.lerp(rawSlate900, other.rawSlate900, t)!,
      rawSlate800: Color.lerp(rawSlate800, other.rawSlate800, t)!,
      rawSlate700: Color.lerp(rawSlate700, other.rawSlate700, t)!,
      rawSlate600: Color.lerp(rawSlate600, other.rawSlate600, t)!,
      rawSlate500: Color.lerp(rawSlate500, other.rawSlate500, t)!,
      rawSlate400: Color.lerp(rawSlate400, other.rawSlate400, t)!,
      rawSlate300: Color.lerp(rawSlate300, other.rawSlate300, t)!,
      rawSlate200: Color.lerp(rawSlate200, other.rawSlate200, t)!,
      rawSlate100: Color.lerp(rawSlate100, other.rawSlate100, t)!,
      rawSlate50: Color.lerp(rawSlate50, other.rawSlate50, t)!,
      rawAmber400: Color.lerp(rawAmber400, other.rawAmber400, t)!,
      rawAmber500: Color.lerp(rawAmber500, other.rawAmber500, t)!,
      rawAmber600: Color.lerp(rawAmber600, other.rawAmber600, t)!,
      rawRed500: Color.lerp(rawRed500, other.rawRed500, t)!,
      rawBlue500: Color.lerp(rawBlue500, other.rawBlue500, t)!,
      rawPurple400: Color.lerp(rawPurple400, other.rawPurple400, t)!,
      rawTeal400: Color.lerp(rawTeal400, other.rawTeal400, t)!,
      rawOrange500: Color.lerp(rawOrange500, other.rawOrange500, t)!,
      rawEmerald500: Color.lerp(rawEmerald500, other.rawEmerald500, t)!,
      rawYellow500: Color.lerp(rawYellow500, other.rawYellow500, t)!,
      rawCyan400: Color.lerp(rawCyan400, other.rawCyan400, t)!,
      bgApp: Color.lerp(bgApp, other.bgApp, t)!,
      bgSurface: Color.lerp(bgSurface, other.bgSurface, t)!,
      bgSurfaceHover: Color.lerp(bgSurfaceHover, other.bgSurfaceHover, t)!,
      bgSurfaceActive: Color.lerp(bgSurfaceActive, other.bgSurfaceActive, t)!,
      borderDefault: Color.lerp(borderDefault, other.borderDefault, t)!,
      borderSubtle: Color.lerp(borderSubtle, other.borderSubtle, t)!,
      borderFocus: Color.lerp(borderFocus, other.borderFocus, t)!,
      textPrimary: Color.lerp(textPrimary, other.textPrimary, t)!,
      textSecondary: Color.lerp(textSecondary, other.textSecondary, t)!,
      textMuted: Color.lerp(textMuted, other.textMuted, t)!,
      textInverse: Color.lerp(textInverse, other.textInverse, t)!,
      accent: Color.lerp(accent, other.accent, t)!,
      accentHover: Color.lerp(accentHover, other.accentHover, t)!,
      accentMuted: Color.lerp(accentMuted, other.accentMuted, t)!,
      destructive: Color.lerp(destructive, other.destructive, t)!,
      cardBg: Color.lerp(cardBg, other.cardBg, t)!,
      cardBorder: Color.lerp(cardBorder, other.cardBorder, t)!,
      tooltipBg: Color.lerp(tooltipBg, other.tooltipBg, t)!,
      tooltipText: Color.lerp(tooltipText, other.tooltipText, t)!,
      btnPrimaryBg: Color.lerp(btnPrimaryBg, other.btnPrimaryBg, t)!,
      btnPrimaryText: Color.lerp(btnPrimaryText, other.btnPrimaryText, t)!,
      dataGov: Color.lerp(dataGov, other.dataGov, t)!,
      dataSociety: Color.lerp(dataSociety, other.dataSociety, t)!,
      dataInfra: Color.lerp(dataInfra, other.dataInfra, t)!,
      dataMonopoly: Color.lerp(dataMonopoly, other.dataMonopoly, t)!,
      dataBaseline: Color.lerp(dataBaseline, other.dataBaseline, t)!,
      dataHousing: Color.lerp(dataHousing, other.dataHousing, t)!,
      dataNegative: Color.lerp(dataNegative, other.dataNegative, t)!,
      dataPositive: Color.lerp(dataPositive, other.dataPositive, t)!,
      dataWarning: Color.lerp(dataWarning, other.dataWarning, t)!,
      dataNeutral: Color.lerp(dataNeutral, other.dataNeutral, t)!,
      spaceXs: lerpDouble(spaceXs, other.spaceXs, t)!,
      spaceSm: lerpDouble(spaceSm, other.spaceSm, t)!,
      spaceMd: lerpDouble(spaceMd, other.spaceMd, t)!,
      spaceLg: lerpDouble(spaceLg, other.spaceLg, t)!,
      spaceXl: lerpDouble(spaceXl, other.spaceXl, t)!,
      space2xl: lerpDouble(space2xl, other.space2xl, t)!,
      space3xl: lerpDouble(space3xl, other.space3xl, t)!,
      radiusAdmin: lerpDouble(radiusAdmin, other.radiusAdmin, t)!,
      radiusPublic: lerpDouble(radiusPublic, other.radiusPublic, t)!,
      radiusButton: lerpDouble(radiusButton, other.radiusButton, t)!,
      radiusTooltip: lerpDouble(radiusTooltip, other.radiusTooltip, t)!,
      durationMicro: t < 0.5 ? durationMicro : other.durationMicro,
      durationData: t < 0.5 ? durationData : other.durationData,
      durationPage: t < 0.5 ? durationPage : other.durationPage,
      chartMode: t < 0.5 ? chartMode : other.chartMode,
      densityMode: t < 0.5 ? densityMode : other.densityMode,
      seriesPrimaryWeight: lerpDouble(seriesPrimaryWeight, other.seriesPrimaryWeight, t)!,
      seriesSecondaryWeight: lerpDouble(seriesSecondaryWeight, other.seriesSecondaryWeight, t)!,
      seriesBenchmarkWeight: lerpDouble(seriesBenchmarkWeight, other.seriesBenchmarkWeight, t)!,
      seriesForecastWeight: lerpDouble(seriesForecastWeight, other.seriesForecastWeight, t)!,
      seriesMutedOpacity: lerpDouble(seriesMutedOpacity, other.seriesMutedOpacity, t)!,
      seriesHoverDim: lerpDouble(seriesHoverDim, other.seriesHoverDim, t)!,
      seriesUncertaintyFillOpacity: lerpDouble(seriesUncertaintyFillOpacity, other.seriesUncertaintyFillOpacity, t)!,
    );
  }
}

/// Returns spacing values for a given [DensityMode] (v3.2 БЛОК 17).
Map<String, double> spacingForDensity(DensityMode mode) {
  switch (mode) {
    case DensityMode.comfortable:
      return {'xs': 4, 'sm': 8, 'md': 16, 'lg': 24, 'xl': 32, '2xl': 48, '3xl': 64};
    case DensityMode.compact:
      return {'xs': 3, 'sm': 6, 'md': 12, 'lg': 18, 'xl': 24, '2xl': 36, '3xl': 48};
    case DensityMode.dense:
      return {'xs': 2, 'sm': 4, 'md': 8, 'lg': 12, 'xl': 16, '2xl': 24, '3xl': 32};
  }
}

/// Builds the complete Summa Vision [ThemeData] with design tokens (v3.2 БЛОК 17).
///
/// Uses Google Fonts: Manrope (display), DM Sans (body),
/// JetBrains Mono (data/monospace).
/// Previously Bricolage Grotesque; swapped because Bricolage lacks Cyrillic glyphs.
/// See docs/phase-3-slice-0-font-blocker-check.md.
ThemeData buildSummaTheme({
  DensityMode density = DensityMode.comfortable,
  ChartMode chartMode = ChartMode.editorial,
}) {
  final spacing = spacingForDensity(density);
  final summa = SummaTheme.dark.copyWith(
    densityMode: density,
    chartMode: chartMode,
    spaceXs: spacing['xs'],
    spaceSm: spacing['sm'],
    spaceMd: spacing['md'],
    spaceLg: spacing['lg'],
    spaceXl: spacing['xl'],
    space2xl: spacing['2xl'],
    space3xl: spacing['3xl'],
  );

  // Typography — exact v3.2 БЛОК 17 values with tabular figures
  const tabularFigures = [FontFeature.tabularFigures()];

  final displayLarge = GoogleFonts.manrope(
    fontSize: 64,
    fontWeight: FontWeight.w700,
    height: 1.0,
    letterSpacing: -1.92,
    fontFeatures: tabularFigures,
    color: summa.textPrimary,
  );

  final bodyLarge = GoogleFonts.dmSans(
    fontSize: 16,
    fontWeight: FontWeight.w400,
    height: 1.6,
    fontFeatures: tabularFigures,
    color: summa.textPrimary,
  );

  final labelSmall = GoogleFonts.jetBrainsMono(
    fontSize: 12,
    fontWeight: FontWeight.w500,
    letterSpacing: 0.6,
    fontFeatures: tabularFigures,
    color: summa.textMuted,
  );

  final bodyFont = GoogleFonts.dmSansTextTheme(
    ThemeData.dark().textTheme,
  );
  final displayFont = GoogleFonts.manropeTextTheme(
    ThemeData.dark().textTheme,
  );
  final dataFont = GoogleFonts.jetBrainsMonoTextTheme(
    ThemeData.dark().textTheme,
  );

  return ThemeData.dark().copyWith(
    extensions: [summa],
    scaffoldBackgroundColor: const Color(0xFF0B0D11),
    colorScheme: ColorScheme.dark(
      primary: summa.accent,
      onPrimary: summa.textInverse,
      secondary: summa.accentHover,
      onSecondary: summa.textInverse,
      error: summa.destructive,
      surface: summa.bgSurface,
      onSurface: summa.textPrimary,
    ),
    appBarTheme: AppBarTheme(
      backgroundColor: summa.bgApp,
      foregroundColor: summa.textPrimary,
      elevation: 0,
      surfaceTintColor: Colors.transparent,
    ),
    cardTheme: CardThemeData(
      color: summa.cardBg,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(summa.radiusAdmin),
        side: BorderSide(color: summa.cardBorder),
      ),
    ),
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: summa.btnPrimaryBg,
        foregroundColor: summa.btnPrimaryText,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(summa.radiusButton),
        ),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: summa.accent,
        side: BorderSide(color: summa.borderDefault),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(summa.radiusButton),
        ),
      ),
    ),
    tooltipTheme: TooltipThemeData(
      decoration: BoxDecoration(
        color: summa.tooltipBg,
        borderRadius: BorderRadius.circular(summa.radiusTooltip),
      ),
      textStyle: TextStyle(color: summa.tooltipText),
    ),
    dividerTheme: DividerThemeData(
      color: summa.borderSubtle,
      thickness: 1,
    ),
    textTheme: bodyFont.copyWith(
      displayLarge: displayLarge,
      displayMedium: displayFont.displayMedium?.copyWith(color: summa.textPrimary),
      displaySmall: displayFont.displaySmall?.copyWith(color: summa.textPrimary),
      headlineLarge: displayFont.headlineLarge?.copyWith(color: summa.textPrimary),
      headlineMedium: displayFont.headlineMedium?.copyWith(color: summa.textPrimary),
      headlineSmall: displayFont.headlineSmall?.copyWith(color: summa.textPrimary),
      titleLarge: bodyFont.titleLarge?.copyWith(color: summa.textPrimary, fontWeight: FontWeight.bold),
      titleMedium: bodyFont.titleMedium?.copyWith(color: summa.textPrimary),
      titleSmall: bodyFont.titleSmall?.copyWith(color: summa.textSecondary),
      bodyLarge: bodyLarge,
      bodyMedium: bodyFont.bodyMedium?.copyWith(color: summa.textSecondary),
      bodySmall: bodyFont.bodySmall?.copyWith(color: summa.textMuted),
      labelLarge: dataFont.labelLarge?.copyWith(color: summa.textPrimary),
      labelMedium: dataFont.labelMedium?.copyWith(color: summa.textSecondary),
      labelSmall: labelSmall,
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: summa.bgSurface,
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(summa.radiusAdmin),
        borderSide: BorderSide(color: summa.borderDefault),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(summa.radiusAdmin),
        borderSide: BorderSide(color: summa.borderDefault),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(summa.radiusAdmin),
        borderSide: BorderSide(color: summa.borderFocus, width: 2),
      ),
      hintStyle: TextStyle(color: summa.textMuted),
    ),
  );
}

/// Helper — mirrors `dart:ui` lerpDouble for non-nullable usage.
double? lerpDouble(double a, double b, double t) {
  return a + (b - a) * t;
}

// ═══════════════════════════════════════════════════════════
// Backward-compatible AppTheme shim
//
// Provides static const Color fields so existing component code
// continues to compile. Migrate to
//   Theme.of(context).extension<SummaTheme>()!
// in Batch 2.
// ═══════════════════════════════════════════════════════════

/// Legacy colour constants — kept for backward compatibility.
///
/// All colours use Design System v3.2 values.
/// Prefer [SummaTheme] via `Theme.of(context).extension<SummaTheme>()!`.
class AppTheme {
  AppTheme._();

  // Background / Surface (updated to v3.2 palette)
  static const Color backgroundDark = Color(0xFF0B0D11);
  static const Color surfaceDark    = Color(0xFF15181E);

  // Neon accents (legacy brand palette, kept until Batch 2 migration)
  static const Color neonGreen      = Color(0xFF00FF94);
  static const Color neonBlue       = Color(0xFF00D4FF);
  static const Color neonPink       = Color(0xFFFF006E);
  static const Color neonYellow     = Color(0xFFFFB700);

  // Text
  static const Color textPrimary    = Color(0xFFF3F4F6);
  static const Color textSecondary  = Color(0xFF8B949E);

  // Status
  static const Color errorRed       = Color(0xFFE11D48);

  /// Full dark [ThemeData] backed by [buildSummaTheme].
  static ThemeData get dark => buildSummaTheme();
}
