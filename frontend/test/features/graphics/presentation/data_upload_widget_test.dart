import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:summa_vision_admin/features/graphics/domain/raw_data_upload.dart';
import 'package:summa_vision_admin/features/graphics/presentation/data_upload_widget.dart';
import 'package:summa_vision_admin/features/graphics/presentation/editable_data_table.dart';

Widget _wrap(Widget child) {
  return MaterialApp(home: Scaffold(body: child));
}

void main() {
  group('DataUploadWidget', () {
    testWidgets('renders the upload button', (tester) async {
      await tester.pumpWidget(
        _wrap(DataUploadWidget(onDataLoaded: (_, __) {})),
      );

      expect(find.byKey(const Key('data_upload_pick_button')), findsOneWidget);
      expect(find.text('Upload JSON / CSV'), findsOneWidget);
    });

    testWidgets('does not render file/summary/error labels by default',
        (tester) async {
      await tester.pumpWidget(
        _wrap(DataUploadWidget(onDataLoaded: (_, __) {})),
      );

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

      await tester.pumpWidget(
        _wrap(
          SizedBox(
            height: 400,
            child: EditableDataTable(
              data: data,
              columns: const ['name', 'score'],
              onCellChanged: (_, __, ___) {},
            ),
          ),
        ),
      );

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
      await tester.pumpWidget(
        _wrap(
          SizedBox(
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

      expect(find.text('Showing 2 of 5 rows'), findsOneWidget);
    });

    testWidgets('tapping a cell then saving emits onCellChanged',
        (tester) async {
      final data = [
        {'name': 'Alice'},
      ];
      String? changedCol;
      int? changedRow;
      String? changedValue;

      await tester.pumpWidget(
        _wrap(
          SizedBox(
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

      await tester.tap(find.text('Alice'));
      await tester.pumpAndSettle();

      expect(find.text('Edit name [row 0]'), findsOneWidget);
      await tester.enterText(find.byType(TextField), 'Alicia');
      await tester.tap(find.text('Save'));
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
