import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../queue/domain/content_brief.dart';
import '../../queue/data/queue_repository.dart';
import 'editor_state.dart';

/// Manages local form state for [EditorScreen].
///
/// Initialised from the [ContentBrief] fetched by [queueProvider].
/// All edits produce a new [EditorState] via copyWith — the original
/// [ContentBrief] is never mutated (it is a freezed immutable object).
class EditorNotifier extends Notifier<EditorState?> {
  @override
  EditorState? build() => null; // null until initialised from a brief

  /// Initialise from a [ContentBrief]. Called once when EditorScreen mounts.
  void initFromBrief(ContentBrief brief) {
    if (state != null && state!.briefId == brief.id)
      return; // already initialised
    state = EditorState(
      briefId: brief.id,
      headline: brief.headline,
      bgPrompt: '', // ContentBrief has no bgPrompt field yet — start empty
      chartType: ChartType.fromApiValue(brief.chartType),
    );
  }

  void updateHeadline(String value) {
    final s = state;
    if (s == null) return;
    state = s.copyWith(headline: value, isDirty: true);
  }

  void updateBgPrompt(String value) {
    final s = state;
    if (s == null) return;
    state = s.copyWith(bgPrompt: value, isDirty: true);
  }

  void updateChartType(ChartType value) {
    final s = state;
    if (s == null) return;
    state = s.copyWith(chartType: value, isDirty: true);
  }

  void reset(ContentBrief brief) {
    state = EditorState(
      briefId: brief.id,
      headline: brief.headline,
      bgPrompt: '',
      chartType: ChartType.fromApiValue(brief.chartType),
    );
  }
}

/// Provider for [EditorNotifier]. Scoped to the editor lifetime.
final editorNotifierProvider = NotifierProvider<EditorNotifier, EditorState?>(
  () => EditorNotifier(),
);
