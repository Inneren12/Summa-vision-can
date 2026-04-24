import '../../../l10n/generated/app_localizations.dart';

/// Domain constants for the chart configuration screen (C-3).
///
/// Each enum maps a Dart-friendly name to the exact API value
/// expected by POST /api/v1/admin/graphics/generate.

// i18n-kept: category D (data-viz terminology) — all 5 chart type display
// names remain English per §3k policy. See docs/phase-3-slice-7-recon.md §6.
// Note: these values use full names (Line Chart, Bar Chart) while editor's
// ChartType.displayName uses short names (Line, Bar). Cross-file inconsistency
// acknowledged and deferred in recon §6.
enum ChartType {
  line('line', 'Line Chart'),
  bar('bar', 'Bar Chart'),
  area('area', 'Area Chart'),
  scatter('scatter', 'Scatter Plot'),
  stackedBar('stacked_bar', 'Stacked Bar');

  final String apiValue;
  final String displayName;
  const ChartType(this.apiValue, this.displayName);
}

// i18n-kept: category D (platform names + aspect ratios) — kept English per
// §3k. See docs/phase-3-slice-7-recon.md §6.
enum SizePreset {
  instagram([1080, 1080], 'Instagram (1:1)'),
  twitter([1200, 628], 'Twitter / X (1.91:1)'),
  reddit([1200, 900], 'Reddit (4:3)');

  final List<int> dimensions;
  final String displayName;
  const SizePreset(this.dimensions, this.displayName);
}

enum BackgroundCategory {
  housing('housing'),
  inflation('inflation'),
  employment('employment'),
  trade('trade'),
  energy('energy'),
  demographics('demographics');

  final String apiValue;
  const BackgroundCategory(this.apiValue);

  /// Localized display label for UI. See §3j — background categories are
  /// localized UI taxonomy (not industry-standard chart terminology).
  String localizedLabel(AppLocalizations l10n) {
    return switch (this) {
      BackgroundCategory.housing      => l10n.backgroundCategoryHousing,
      BackgroundCategory.inflation    => l10n.backgroundCategoryInflation,
      BackgroundCategory.employment   => l10n.backgroundCategoryEmployment,
      BackgroundCategory.trade        => l10n.backgroundCategoryTrade,
      BackgroundCategory.energy       => l10n.backgroundCategoryEnergy,
      BackgroundCategory.demographics => l10n.backgroundCategoryDemographics,
    };
  }
}
