import 'package:freezed_annotation/freezed_annotation.dart';

part 'editor_state.freezed.dart';

/// All 13 chart types supported by the Visual Engine (PR-17b).
/// Must stay in sync with Python [ChartType] enum in schemas.py.
enum ChartType {
  line,
  bar,
  scatter,
  area,
  stackedBar,
  heatmap,
  candlestick,
  pie,
  donut,
  waterfall,
  treemap,
  bubble,
  choropleth;

  /// Wire value sent to the backend (matches Python ChartType string values).
  String get apiValue => switch (this) {
    ChartType.line => 'LINE',
    ChartType.bar => 'BAR',
    ChartType.scatter => 'SCATTER',
    ChartType.area => 'AREA',
    ChartType.stackedBar => 'STACKED_BAR',
    ChartType.heatmap => 'HEATMAP',
    ChartType.candlestick => 'CANDLESTICK',
    ChartType.pie => 'PIE',
    ChartType.donut => 'DONUT',
    ChartType.waterfall => 'WATERFALL',
    ChartType.treemap => 'TREEMAP',
    ChartType.bubble => 'BUBBLE',
    ChartType.choropleth => 'CHOROPLETH',
  };

  /// Display label shown in the dropdown.
  String get displayName => switch (this) {
    ChartType.line => 'Line',
    ChartType.bar => 'Bar',
    ChartType.scatter => 'Scatter',
    ChartType.area => 'Area',
    ChartType.stackedBar => 'Stacked Bar',
    ChartType.heatmap => 'Heatmap',
    ChartType.candlestick => 'Candlestick',
    ChartType.pie => 'Pie',
    ChartType.donut => 'Donut',
    ChartType.waterfall => 'Waterfall',
    ChartType.treemap => 'Treemap',
    ChartType.bubble => 'Bubble',
    ChartType.choropleth => 'Choropleth (Canada)',
  };

  /// Parse from backend string value.
  static ChartType fromApiValue(String value) {
    return ChartType.values.firstWhere(
      (e) => e.apiValue == value.toUpperCase(),
      orElse: () => ChartType.bar,
    );
  }
}

/// Mutable local state for the editor form.
///
/// Derived from an immutable [ContentBrief] but held in a [Notifier]
/// so form edits never mutate the original object.
@freezed
class EditorState with _$EditorState {
  const factory EditorState({
    required int briefId,
    required String headline,
    required String bgPrompt,
    required ChartType chartType,
    @Default(false) bool isDirty,
  }) = _EditorState;
}
