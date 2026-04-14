import 'package:flutter/material.dart';

/// Simple inline-editable preview table for uploaded data.
///
/// Shows at most 100 rows so that pathological uploads don't pathologically
/// size the widget tree.  Tapping a cell opens a dialog that emits an
/// [onCellChanged] callback when the user commits a new value.
class EditableDataTable extends StatelessWidget {
  const EditableDataTable({
    super.key,
    required this.data,
    required this.columns,
    required this.onCellChanged,
    this.maxRows = 100,
  });

  final List<Map<String, dynamic>> data;
  final List<String> columns;
  final void Function(int row, String column, String newValue) onCellChanged;
  final int maxRows;

  @override
  Widget build(BuildContext context) {
    final displayRows = data.take(maxRows).toList();
    final hasMore = data.length > maxRows;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: DataTable(
            key: const Key('editable_data_table'),
            columns: columns
                .map((col) => DataColumn(label: Text(col)))
                .toList(),
            rows: displayRows.asMap().entries.map((entry) {
              final rowIdx = entry.key;
              final row = entry.value;
              return DataRow(
                key: ValueKey('editable_row_$rowIdx'),
                cells: columns.map((col) {
                  final value = row[col]?.toString() ?? '';
                  return DataCell(
                    Text(value),
                    onTap: () => _editCell(context, rowIdx, col, value),
                  );
                }).toList(),
              );
            }).toList(),
          ),
        ),
        if (hasMore)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Text(
              'Showing $maxRows of ${data.length} rows',
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ),
      ],
    );
  }

  Future<void> _editCell(
    BuildContext context,
    int row,
    String column,
    String currentValue,
  ) async {
    final controller = TextEditingController(text: currentValue);
    final newValue = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('Edit $column [row $row]'),
        content: TextField(
          controller: controller,
          autofocus: true,
          onSubmitted: (v) => Navigator.of(ctx).pop(v),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(ctx).pop(controller.text),
            child: const Text('Save'),
          ),
        ],
      ),
    );

    if (newValue != null && newValue != currentValue) {
      onCellChanged(row, column, newValue);
    }
  }
}
