/// Domain constants for the chart configuration screen (C-3).
///
/// Each enum maps a Dart-friendly name to the exact API value
/// expected by POST /api/v1/admin/graphics/generate.

enum ChartType {
  line('line', 'Line Chart'),
  bar('bar', 'Bar Chart'),
  area('area', 'Area Chart'),
  scatter('scatter', 'Scatter Plot'),
  stackedBar('stacked_bar', 'Stacked Bar'),
  heatmap('heatmap', 'Heatmap');

  final String apiValue;
  final String displayName;
  const ChartType(this.apiValue, this.displayName);
}

enum SizePreset {
  instagram([1080, 1080], 'Instagram (1:1)'),
  twitter([1200, 628], 'Twitter / X (1.91:1)'),
  reddit([1200, 900], 'Reddit (4:3)');

  final List<int> dimensions;
  final String displayName;
  const SizePreset(this.dimensions, this.displayName);
}

enum BackgroundCategory {
  housing('housing', 'Housing'),
  inflation('inflation', 'Inflation'),
  employment('employment', 'Employment'),
  trade('trade', 'Trade'),
  energy('energy', 'Energy'),
  demographics('demographics', 'Demographics');

  final String apiValue;
  final String displayName;
  const BackgroundCategory(this.apiValue, this.displayName);
}
