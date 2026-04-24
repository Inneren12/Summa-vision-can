import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:summa_vision_admin/features/graphics/domain/raw_data_upload.dart';
import 'package:summa_vision_admin/features/graphics/presentation/data_upload_widget.dart';
import 'package:summa_vision_admin/features/graphics/presentation/editable_data_table.dart';
import 'package:summa_vision_admin/l10n/generated/app_localizations.dart';

import '../../../helpers/localized_pump.dart';

AppLocalizations _l10n(WidgetTester tester, Type targetType) {
  final ctx = tester.element(find.byType(targetType));
  return AppLocalizations.of(ctx)!;
}

void main() {
  group('DataUploadWidget', () {
    testWidgets('renders the upload button', (tester) async {
      await pumpLocalizedWidget(
        tester,
        Scaffold(body: DataUploadWidget(onDataLoaded: (_, __) {})),
      );
      await tester.pumpAndSettle();

      final l10n = _l10n(tester, DataUploadWidget);
      expect(find.byKey(const Key('data_upload_pick_button')), findsOneWidget);
      expect(find.text(l10n.chartConfigUploadPickButton), findsOneWidget);
    });

    testWidgets('does not render file/summary/error labels by default',
        (tester) async {
      await pumpLocalizedWidget(
        tester,
        Scaffold(body: DataUploadWidget(onDataLoaded: (_, __) {})),
      );
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('data_upload_file_label')), findsNothing);
      expect(find.byKey(const Key('data_upload_summary')), findsNothing);
      expect(find.byKey(const Key('data_upload_error')), findsNothing);
    });
  });

  group('EditableDataTable', () {
    testWidgets('renders all columns and rows', (tester) async {
      final data = [
        {'name': 'Alice', 'score': 95},
        {'name': 'Bob', 'score': 87},
      ];

      await pumpLocalizedWidget(
        tester,
        Scaffold(
          body: SizedBox(
            height: 400,
            child: EditableDataTable(
              data: data,
              columns: const ['name', 'score'],
              onCellChanged: (_, __, ___) {},
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('editable_data_table')), findsOneWidget);
      expect(find.text('name'), findsOneWidget);
      expect(find.text('score'), findsOneWidget);
      expect(find.text('Alice'), findsOneWidget);
      expect(find.text('Bob'), findsOneWidget);
      expect(find.text('95'), findsOneWidget);
    });

    testWidgets('shows truncation hint when rows exceed maxRows',
        (tester) async {
      final data = List<Map<String, dynamic>>.generate(
        5,
        (i) => {'x': i},
      );
      await pumpLocalizedWidget(
        tester,
        Scaffold(
          body: SizedBox(
            height: 400,
            child: EditableDataTable(
              data: data,
              columns: const ['x'],
              maxRows: 2,
              onCellChanged: (_, __, ___) {},
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();

      final l10n = _l10n(tester, EditableDataTable);
      expect(find.text(l10n.chartConfigTableShowingRows(2, 5)), findsOneWidget);
    });

    testWidgets('tapping a cell then saving emits onCellChanged',
        (tester) async {
      final data = [
        {'name': 'Alice'},
      ];
      String? changedCol;
      int? changedRow;
      String? changedValue;

      await pumpLocalizedWidget(
        tester,
        Scaffold(
          body: SizedBox(
            height: 400,
            child: EditableDataTable(
              data: data,
              columns: const ['name'],
              onCellChanged: (row, col, val) {
                changedRow = row;
                changedCol = col;
                changedValue = val;
              },
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();

      final l10n = _l10n(tester, EditableDataTable);

      await tester.tap(find.text('Alice'));
      await tester.pumpAndSettle();

      expect(find.text(l10n.chartConfigTableEditCellTitle('name', 0)), findsOneWidget);
      await tester.enterText(find.byType(TextField), 'Alicia');
      await tester.tap(find.text(l10n.commonSaveVerb));
      await tester.pumpAndSettle();

      expect(changedRow, 0);
      expect(changedCol, 'name');
      expect(changedValue, 'Alicia');
    });
  });

  group('RawDataColumn sanity', () {
    test('column names propagate into the widget list', () {
      final cols = [
        const RawDataColumn(name: 'year', dtype: 'int'),
        const RawDataColumn(name: 'value', dtype: 'float'),
      ];
      expect(cols.map((c) => c.name).toList(), ['year', 'value']);
      expect(cols.map((c) => c.dtype).toList(), ['int', 'float']);
    });
  });
}
