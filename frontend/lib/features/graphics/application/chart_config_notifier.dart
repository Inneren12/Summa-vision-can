import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:freezed_annotation/freezed_annotation.dart';

import '../domain/chart_constants.dart';

part 'chart_config_notifier.freezed.dart';

@freezed
class ChartConfig with _$ChartConfig {
  const factory ChartConfig({
    required String dataKey,
    String? sourceProductId,
    @Default(ChartType.line) ChartType chartType,
    @Default(SizePreset.instagram) SizePreset sizePreset,
    @Default(BackgroundCategory.housing) BackgroundCategory category,
    @Default('') String title,
  }) = _ChartConfig;
}

class ChartConfigNotifier extends Notifier<ChartConfig> {
  @override
  ChartConfig build() => const ChartConfig(dataKey: '');

  void setDataKey(String key, {String? productId}) =>
      state = state.copyWith(dataKey: key, sourceProductId: productId);

  /// Full reset — used when the operator navigates to a different dataset.
  void reset(String dataKey, {String? sourceProductId}) {
    state = ChartConfig(
      dataKey: dataKey,
      sourceProductId: sourceProductId,
    );
  }

  void setChartType(ChartType type) =>
      state = state.copyWith(chartType: type);

  void setSizePreset(SizePreset preset) =>
      state = state.copyWith(sizePreset: preset);

  void setCategory(BackgroundCategory cat) =>
      state = state.copyWith(category: cat);

  void setTitle(String title) => state = state.copyWith(title: title);
}

final chartConfigNotifierProvider =
    NotifierProvider<ChartConfigNotifier, ChartConfig>(
  () => ChartConfigNotifier(),
);
