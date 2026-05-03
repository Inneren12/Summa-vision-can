import 'package:flutter/material.dart';

/// Key/value editor for the ``dimension_filters`` form field.
///
/// Pure Material widgets — no reorder UX (DEBT-055 defers it).
class DimensionFiltersEditor extends StatefulWidget {
  const DimensionFiltersEditor({
    super.key,
    required this.value,
    required this.onChanged,
    this.dimensionErrors = const {},
  });

  /// Current value as a name → name dict.
  final Map<String, String> value;

  /// Called whenever a row is added/removed/edited.
  final ValueChanged<Map<String, String>> onChanged;

  /// Per-dimension server-side error messages (e.g. ``DIMENSION_NOT_FOUND``).
  final Map<String, String> dimensionErrors;

  @override
  State<DimensionFiltersEditor> createState() =>
      _DimensionFiltersEditorState();
}

class _DimensionFiltersEditorState extends State<DimensionFiltersEditor> {
  late List<MapEntry<String, String>> _rows;

  @override
  void initState() {
    super.initState();
    _rows = widget.value.entries.toList(growable: true);
  }

  void _emit() {
    final map = <String, String>{
      for (final e in _rows)
        if (e.key.trim().isNotEmpty) e.key: e.value,
    };
    widget.onChanged(map);
  }

  void _addRow() {
    setState(() => _rows.add(const MapEntry('', '')));
    _emit();
  }

  void _removeRow(int index) {
    setState(() => _rows.removeAt(index));
    _emit();
  }

  void _updateKey(int index, String newKey) {
    setState(() {
      final value = _rows[index].value;
      _rows[index] = MapEntry(newKey, value);
    });
    _emit();
  }

  void _updateValue(int index, String newValue) {
    setState(() {
      final key = _rows[index].key;
      _rows[index] = MapEntry(key, newValue);
    });
    _emit();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        for (var i = 0; i < _rows.length; i++)
          Padding(
            key: ValueKey('dim-row-$i'),
            padding: const EdgeInsets.symmetric(vertical: 4),
            child: _DimensionFilterRow(
              dimension: _rows[i].key,
              member: _rows[i].value,
              error: widget.dimensionErrors[_rows[i].key],
              onDimensionChanged: (v) => _updateKey(i, v),
              onMemberChanged: (v) => _updateValue(i, v),
              onRemove: () => _removeRow(i),
            ),
          ),
        Align(
          alignment: Alignment.centerLeft,
          child: TextButton.icon(
            key: const ValueKey('dim-add-row'),
            onPressed: _addRow,
            icon: const Icon(Icons.add),
            label: const Text('Add filter'),
          ),
        ),
      ],
    );
  }
}

class _DimensionFilterRow extends StatelessWidget {
  const _DimensionFilterRow({
    required this.dimension,
    required this.member,
    required this.error,
    required this.onDimensionChanged,
    required this.onMemberChanged,
    required this.onRemove,
  });

  final String dimension;
  final String member;
  final String? error;
  final ValueChanged<String> onDimensionChanged;
  final ValueChanged<String> onMemberChanged;
  final VoidCallback onRemove;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(
          child: TextFormField(
            key: ValueKey('dim-key-$dimension'),
            initialValue: dimension,
            decoration: InputDecoration(
              labelText: 'Dimension',
              errorText: error,
              border: const OutlineInputBorder(),
            ),
            onChanged: onDimensionChanged,
          ),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: TextFormField(
            key: ValueKey('dim-value-$dimension'),
            initialValue: member,
            decoration: const InputDecoration(
              labelText: 'Member',
              border: OutlineInputBorder(),
            ),
            onChanged: onMemberChanged,
          ),
        ),
        IconButton(
          tooltip: 'Remove filter',
          icon: const Icon(Icons.delete_outline),
          onPressed: onRemove,
        ),
      ],
    );
  }
}
