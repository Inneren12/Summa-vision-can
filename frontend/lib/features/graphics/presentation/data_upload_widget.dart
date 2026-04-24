import 'dart:convert';

import 'package:csv/csv.dart';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';

import '../../../l10n/generated/app_localizations.dart';
import '../domain/raw_data_upload.dart';

/// Widget that lets the admin pick a JSON or CSV file and emits the parsed
/// rows + inferred column dtypes back to its parent via [onDataLoaded].
///
/// * JSON: accepts either a top-level array of objects or
///   ``{ "data": [ ... ] }`` wrapping.
/// * CSV:  first row is treated as the header.
/// * Dtypes are inferred from a sample of the first 20 non-empty values.
class DataUploadWidget extends StatefulWidget {
  const DataUploadWidget({super.key, required this.onDataLoaded});

  /// Called after a successful parse. ``data`` is the raw rows, ``columns``
  /// gives one [RawDataColumn] per key discovered in the first row.
  final void Function(
    List<Map<String, dynamic>> data,
    List<RawDataColumn> columns,
  ) onDataLoaded;

  @override
  State<DataUploadWidget> createState() => _DataUploadWidgetState();
}

class _DataUploadWidgetState extends State<DataUploadWidget> {
  List<Map<String, dynamic>>? _data;
  List<RawDataColumn>? _columns;
  String? _fileName;
  String? _error;

  Future<void> _pickFile(AppLocalizations l10n) async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: const ['json', 'csv'],
      withData: true,
    );
    if (result == null || result.files.isEmpty) return;

    final file = result.files.first;
    final bytes = file.bytes;
    if (bytes == null) return;

    final content = utf8.decode(bytes);
    try {
      if (file.extension == 'json') {
        _parseJson(content);
      } else if (file.extension == 'csv') {
        _parseCsv(content);
      } else {
        throw const FormatException('Unsupported file type — pick JSON or CSV');
      }
      setState(() {
        _fileName = file.name;
        _error = null;
      });
      widget.onDataLoaded(_data!, _columns!);
    } catch (e) {
      setState(() {
        _error = l10n.chartConfigUploadParseError(e.toString());
        _data = null;
        _columns = null;
      });
    }
  }

  void _parseJson(String content) {
    final decoded = jsonDecode(content);
    List<Map<String, dynamic>> rows;
    if (decoded is List) {
      rows = decoded
          .whereType<Map>()
          .map((m) => Map<String, dynamic>.from(m))
          .toList();
    } else if (decoded is Map && decoded['data'] is List) {
      rows = (decoded['data'] as List)
          .whereType<Map>()
          .map((m) => Map<String, dynamic>.from(m))
          .toList();
    } else {
      throw const FormatException('JSON must be an array or {"data": [...] }');
    }
    if (rows.isEmpty) {
      throw const FormatException('No data rows');
    }
    _data = rows;
    _columns = rows.first.keys
        .map((k) => RawDataColumn(name: k, dtype: _inferType(rows, k)))
        .toList(growable: false);
  }

  void _parseCsv(String content) {
    final raw = const CsvToListConverter(eol: '\n').convert(content);
    if (raw.length < 2) {
      throw const FormatException('CSV must have a header row and >=1 data row');
    }
    final headers = raw.first.map((h) => h.toString()).toList();
    final rows = <Map<String, dynamic>>[];
    for (final row in raw.skip(1)) {
      final map = <String, dynamic>{};
      for (var i = 0; i < headers.length && i < row.length; i++) {
        map[headers[i]] = row[i];
      }
      rows.add(map);
    }
    _data = rows;
    _columns = headers
        .map((h) => RawDataColumn(name: h, dtype: _inferType(rows, h)))
        .toList(growable: false);
  }

  String _inferType(List<Map<String, dynamic>> rows, String key) {
    final sample = rows
        .take(20)
        .map((row) => row[key]?.toString() ?? '')
        .where((v) => v.isNotEmpty)
        .toList();
    if (sample.isEmpty) return 'str';

    if (sample.every((v) => int.tryParse(v) != null)) return 'int';
    if (sample.every((v) => double.tryParse(v) != null)) return 'float';

    final dateRegex = RegExp(r'^\d{4}-\d{2}-\d{2}');
    if (sample.every((v) => dateRegex.hasMatch(v))) return 'date';
    return 'str';
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context)!;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        FilledButton.icon(
          key: const Key('data_upload_pick_button'),
          onPressed: () => _pickFile(l10n),
          icon: const Icon(Icons.upload_file),
          label: Text(l10n.chartConfigUploadPickButton),
        ),
        if (_fileName != null)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Text(
              l10n.chartConfigUploadFileLabel(_fileName!),
              key: const Key('data_upload_file_label'),
              style: theme.textTheme.bodySmall,
            ),
          ),
        if (_error != null)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Text(
              _error!,
              key: const Key('data_upload_error'),
              style: TextStyle(color: theme.colorScheme.error),
            ),
          ),
        if (_data != null && _columns != null)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Text(
              l10n.chartConfigUploadSummary(_data!.length, _columns!.length),
              key: const Key('data_upload_summary'),
              style: theme.textTheme.bodySmall,
            ),
          ),
      ],
    );
  }
}
