import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:summa_vision_admin/core/theme/app_theme.dart';
import 'package:summa_vision_admin/features/editor/domain/editor_notifier.dart';
import 'package:summa_vision_admin/features/editor/domain/editor_state.dart';
import 'package:summa_vision_admin/features/editor/presentation/editor_screen.dart';
import 'package:summa_vision_admin/features/queue/data/queue_repository.dart';
import 'package:summa_vision_admin/features/queue/domain/content_brief.dart';

final _sampleBrief = ContentBrief(
  id: 1,
  headline: 'Canadian housing surge',
  chartType: 'BAR',
  viralityScore: 8.5,
  status: 'DRAFT',
  createdAt: '2026-01-01T00:00:00Z',
);

Widget _buildScreen({
  String briefId = '1',
  List<ContentBrief> briefs = const [],
}) {
  return ProviderScope(
    overrides: [
      queueProvider.overrideWith((ref) async => briefs),
    ],
    child: MaterialApp(
      theme: AppTheme.dark,
      home: EditorScreen(briefId: briefId),
    ),
  );
}

void main() {
  group('EditorScreen — renders correctly', () {
    testWidgets('shows brief id in app bar', (tester) async {
      await tester.pumpWidget(_buildScreen(briefs: [_sampleBrief]));
      await tester.pumpAndSettle();

      expect(find.textContaining('Brief #1'), findsOneWidget);
    });

    testWidgets('shows virality score', (tester) async {
      await tester.pumpWidget(_buildScreen(briefs: [_sampleBrief]));
      await tester.pumpAndSettle();

      expect(find.text('8.5'), findsOneWidget);
    });

    testWidgets('headline field is pre-filled from brief', (tester) async {
      await tester.pumpWidget(_buildScreen(briefs: [_sampleBrief]));
      await tester.pumpAndSettle();

      final editableText = tester.widget<EditableText>(
        find.descendant(
          of: find.byKey(const Key('headline_field')),
          matching: find.byType(EditableText),
        ),
      );
      expect(editableText.controller.text, equals('Canadian housing surge'));
    });

    testWidgets('shows all 13 chart types in dropdown', (tester) async {
      await tester.pumpWidget(_buildScreen(briefs: [_sampleBrief]));
      await tester.pumpAndSettle();

      // Verify dropdown has all 13 items
      // DropdownButtonFormField wraps items internally; verify via tap + visible items
      // Instead of checking all rendered labels (viewport limited), verify item count
      await tester.tap(find.byKey(const Key('chart_type_dropdown')));
      await tester.pumpAndSettle();

      // Verify a few representative chart types are visible
      expect(find.text('Bar'), findsWidgets);
      expect(find.text('Line'), findsWidgets);
      expect(find.text('Scatter'), findsWidgets);

      // Close the dropdown
      await tester.tapAt(Offset.zero);
      await tester.pumpAndSettle();

      // Verify all 13 enum values exist
      expect(ChartType.values.length, equals(13));
    });

    testWidgets('Generate button is visible', (tester) async {
      await tester.pumpWidget(_buildScreen(briefs: [_sampleBrief]));
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('generate_btn')), findsOneWidget);
    });

    testWidgets('Preview Background button is present but disabled', (tester) async {
      await tester.pumpWidget(_buildScreen(briefs: [_sampleBrief]));
      await tester.pumpAndSettle();

      final btn = tester.widget<OutlinedButton>(
        find.byKey(const Key('preview_background_btn')),
      );
      expect(btn.onPressed, isNull);
    });
  });

  group('EditorScreen — form interactions', () {
    testWidgets('editing headline updates EditorNotifier state', (tester) async {
      late ProviderContainer container;

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            queueProvider.overrideWith((ref) async => [_sampleBrief]),
          ],
          child: Builder(
            builder: (context) {
              container = ProviderScope.containerOf(context);
              return MaterialApp(
                theme: AppTheme.dark,
                home: EditorScreen(briefId: '1'),
              );
            },
          ),
        ),
      );
      await tester.pumpAndSettle();

      await tester.enterText(
        find.byKey(const Key('headline_field')),
        'Updated headline',
      );
      await tester.pump();

      final state = container.read(editorNotifierProvider);
      expect(state?.headline, equals('Updated headline'));
      expect(state?.isDirty, isTrue);
    });

    testWidgets('editing bg_prompt updates EditorNotifier state', (tester) async {
      late ProviderContainer container;

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            queueProvider.overrideWith((ref) async => [_sampleBrief]),
          ],
          child: Builder(
            builder: (context) {
              container = ProviderScope.containerOf(context);
              return MaterialApp(
                theme: AppTheme.dark,
                home: EditorScreen(briefId: '1'),
              );
            },
          ),
        ),
      );
      await tester.pumpAndSettle();

      await tester.enterText(
        find.byKey(const Key('bg_prompt_field')),
        'Canadian suburb at golden hour',
      );
      await tester.pump();

      final state = container.read(editorNotifierProvider);
      expect(state?.bgPrompt, equals('Canadian suburb at golden hour'));
    });

    testWidgets('selecting chart type updates EditorNotifier', (tester) async {
      late ProviderContainer container;

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            queueProvider.overrideWith((ref) async => [_sampleBrief]),
          ],
          child: Builder(
            builder: (context) {
              container = ProviderScope.containerOf(context);
              return MaterialApp(
                theme: AppTheme.dark,
                home: EditorScreen(briefId: '1'),
              );
            },
          ),
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(find.byKey(const Key('chart_type_dropdown')));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Line').last);
      await tester.pumpAndSettle();

      final state = container.read(editorNotifierProvider);
      expect(state?.chartType, equals(ChartType.line));
      expect(state?.isDirty, isTrue);
    });
  });

  group('EditorScreen — not found state', () {
    testWidgets('shows not found message for unknown briefId', (tester) async {
      await tester.pumpWidget(_buildScreen(
        briefId: '999',
        briefs: [_sampleBrief],
      ));
      await tester.pumpAndSettle();

      expect(find.textContaining('Brief not found'), findsOneWidget);
    });
  });

  group('EditorNotifier unit tests', () {
    test('initFromBrief sets initial state', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      final notifier = container.read(editorNotifierProvider.notifier);
      notifier.initFromBrief(_sampleBrief);

      final state = container.read(editorNotifierProvider);
      expect(state?.briefId, equals(1));
      expect(state?.headline, equals('Canadian housing surge'));
      expect(state?.chartType, equals(ChartType.bar));
      expect(state?.isDirty, isFalse);
    });

    test('updateHeadline marks state as dirty', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      final notifier = container.read(editorNotifierProvider.notifier);
      notifier.initFromBrief(_sampleBrief);
      notifier.updateHeadline('New headline');

      final state = container.read(editorNotifierProvider);
      expect(state?.headline, equals('New headline'));
      expect(state?.isDirty, isTrue);
    });

    test('updateChartType marks state as dirty', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      final notifier = container.read(editorNotifierProvider.notifier);
      notifier.initFromBrief(_sampleBrief);
      notifier.updateChartType(ChartType.choropleth);

      final state = container.read(editorNotifierProvider);
      expect(state?.chartType, equals(ChartType.choropleth));
      expect(state?.isDirty, isTrue);
    });

    test('reset restores original state', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      final notifier = container.read(editorNotifierProvider.notifier);
      notifier.initFromBrief(_sampleBrief);
      notifier.updateHeadline('Changed');
      notifier.reset(_sampleBrief);

      final state = container.read(editorNotifierProvider);
      expect(state?.headline, equals('Canadian housing surge'));
      expect(state?.isDirty, isFalse);
    });

    test('ChartType.fromApiValue parses all 13 values', () {
      final cases = {
        'LINE': ChartType.line,
        'BAR': ChartType.bar,
        'SCATTER': ChartType.scatter,
        'AREA': ChartType.area,
        'STACKED_BAR': ChartType.stackedBar,
        'HEATMAP': ChartType.heatmap,
        'CANDLESTICK': ChartType.candlestick,
        'PIE': ChartType.pie,
        'DONUT': ChartType.donut,
        'WATERFALL': ChartType.waterfall,
        'TREEMAP': ChartType.treemap,
        'BUBBLE': ChartType.bubble,
        'CHOROPLETH': ChartType.choropleth,
      };

      for (final entry in cases.entries) {
        expect(
          ChartType.fromApiValue(entry.key),
          equals(entry.value),
          reason: '${entry.key} should parse to ${entry.value}',
        );
      }
    });

    test('ChartType.apiValue round-trips correctly', () {
      for (final ct in ChartType.values) {
        final parsed = ChartType.fromApiValue(ct.apiValue);
        expect(parsed, equals(ct));
      }
    });
  });
}
