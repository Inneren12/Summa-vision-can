import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_theme.dart';
import '../../../l10n/generated/app_localizations.dart';
import '../application/cube_diff_service.dart';
import '../application/data_preview_providers.dart';
import '../domain/data_preview_response.dart';
import '../domain/preview_filter.dart';

/// Data Preview Screen (C-2).
///
/// Displays a tabular preview of up to 100 rows from a processed Parquet file.
/// Provides column schema inspection, client-side filtering, and sorting.
class DataPreviewScreen extends ConsumerStatefulWidget {
  const DataPreviewScreen({super.key, required this.storageKey});

  final String storageKey;

  @override
  ConsumerState<DataPreviewScreen> createState() => _DataPreviewScreenState();
}

class _DataPreviewScreenState extends ConsumerState<DataPreviewScreen> {
  final _searchController = TextEditingController();
  final _dateFromController = TextEditingController();
  final _dateToController = TextEditingController();
  Timer? _debounce;
  bool _schemaExpanded = false;

  SummaTheme get _theme => Theme.of(context).extension<SummaTheme>()!;

  @override
  void initState() {
    super.initState();
    // Set the storage key provider so dataPreviewProvider fetches data.
    Future.microtask(() {
      ref.read(previewStorageKeyProvider.notifier).state = widget.storageKey;
    });
  }

  @override
  void dispose() {
    _searchController.dispose();
    _dateFromController.dispose();
    _dateToController.dispose();
    _debounce?.cancel();
    super.dispose();
  }

  void _onSearchChanged(String value) {
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 300), () {
      ref.read(previewFilterProvider.notifier).state =
          ref.read(previewFilterProvider).copyWith(searchText: value);
    });
  }

  void _clearFilters() {
    _searchController.clear();
    _dateFromController.clear();
    _dateToController.clear();
    ref.read(previewFilterProvider.notifier).state = const PreviewFilter();
  }

  void _onSort(String columnName) {
    final current = ref.read(previewSortColumnProvider);
    if (current == columnName) {
      final asc = ref.read(previewSortAscendingProvider);
      ref.read(previewSortAscendingProvider.notifier).state = !asc;
    } else {
      ref.read(previewSortColumnProvider.notifier).state = columnName;
      ref.read(previewSortAscendingProvider.notifier).state = true;
    }
  }

  /// Extract a human-readable label from the storage key.
  String _readableKey(String key) {
    final parts = key.split('/');
    if (parts.length >= 2) {
      final file = parts.last.replaceAll('.parquet', '');
      final productId = parts[parts.length - 2];
      return '$productId / $file';
    }
    return key;
  }

  /// Infer a display dtype from a runtime value (used for schema chips
  /// since the backend doesn't return dtype info in the preview endpoint).
  String _inferDtype(dynamic value) {
    if (value == null) return 'str';
    if (value is int) return 'int64';
    if (value is double) return 'float64';
    return 'str';
  }

  @override
  Widget build(BuildContext context) {
    final previewAsync = ref.watch(dataPreviewProvider);
    final filteredRows = ref.watch(filteredPreviewRowsProvider);
    final sortCol = ref.watch(previewSortColumnProvider);
    final sortAsc = ref.watch(previewSortAscendingProvider);
    final diffAsync = ref.watch(cubeDiffProvider);
    final l10n = AppLocalizations.of(context);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Data Preview'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.go('/cubes/search'),
        ),
      ),
      body: previewAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (err, _) => Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.error_outline,
                  color: _theme.destructive, size: 48),
              const SizedBox(height: 16),
              Text(
                'Failed to load preview\n$err',
                textAlign: TextAlign.center,
                style: TextStyle(color: _theme.textSecondary),
              ),
              const SizedBox(height: 16),
              ElevatedButton(
                onPressed: () => ref.invalidate(dataPreviewProvider),
                child: const Text('Retry'),
              ),
            ],
          ),
        ),
        data: (preview) {
          if (preview == null) {
            return Center(
              child: Text(
                'No data to preview',
                style: TextStyle(color: _theme.textSecondary),
              ),
            );
          }

          final diff = diffAsync.valueOrNull ?? const CubeDiff.noBaseline();
          final diffBanner = diffAsync.when(
            data: (value) => switch (value) {
              NoBaselineCubeDiff() => Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                  child: Text(
                    preview.productId == null
                        ? (l10n?.dataPreviewDiffNoProductId ??
                            'This data has no diff tracking')
                        : (l10n?.dataPreviewDiffNoBaseline ??
                            'First view — no comparison available'),
                    style: TextStyle(color: _theme.textSecondary, fontSize: 12),
                  ),
                ),
              SchemaChangedCubeDiff() => Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                  child: Text(
                    l10n?.dataPreviewDiffSchemaChanged ??
                        'Schema changed since last view — diff unavailable',
                    style: TextStyle(color: _theme.textSecondary, fontSize: 12),
                  ),
                ),
              ComputedCubeDiff(:final changedCells) => Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                  child: Text(
                    l10n?.dataPreviewDiffStatusLabel(changedCells.length) ??
                        (changedCells.length == 1
                            ? '1 cell changed since last view'
                            : '${changedCells.length} cells changed since last view'),
                    style: TextStyle(color: _theme.textSecondary, fontSize: 12),
                  ),
                ),
            },
            loading: SizedBox.shrink,
            error: (_, __) => SizedBox.shrink(),
          );

          return Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // A) Header / Info Bar
              _buildInfoBar(preview),

              // B) Schema Inspector
              _buildSchemaInspector(preview),

              // C) Filter Controls
              _buildFilterToolbar(preview),

              diffBanner,

              // D) Data Table
              Expanded(
                child: _buildDataTable(
                  preview.columnNames,
                  filteredRows,
                  sortCol,
                  sortAsc,
                  preview,
                  diff,
                ),
              ),

              // E) Actions Bar
              _buildActionsBar(),
            ],
          );
        },
      ),
    );
  }

  /// Format an integer with comma grouping (e.g. 48520 → "48,520").
  String _formatInt(int n) {
    final s = n.toString();
    final buf = StringBuffer();
    for (var i = 0; i < s.length; i++) {
      if (i > 0 && (s.length - i) % 3 == 0) buf.write(',');
      buf.write(s[i]);
    }
    return buf.toString();
  }

  Widget _buildInfoBar(DataPreviewResponse preview) {
    final returnedRows = preview.data.length;
    final totalRows = preview.rows;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      color: _theme.bgSurface,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            _readableKey(preview.storageKey),
            style: TextStyle(
              color: _theme.dataGov,
              fontSize: 14,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 4),
          Row(
            children: [
              Text(
                'Showing ${_formatInt(returnedRows)} of ${_formatInt(totalRows)} rows',
                style: TextStyle(
                  color: _theme.textPrimary,
                  fontSize: 13,
                ),
              ),
              if (totalRows > returnedRows) ...[
                const SizedBox(width: 8),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                  decoration: BoxDecoration(
                    color: _theme.dataWarning.withOpacity(0.15),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text(
                    'Preview limited to first 100 rows',
                    style: TextStyle(
                      color: _theme.dataWarning,
                      fontSize: 11,
                    ),
                  ),
                ),
              ],
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildSchemaInspector(DataPreviewResponse preview) {
    // Infer dtypes from the first data row if available
    final firstRow =
        preview.data.isNotEmpty ? preview.data.first : <String, dynamic>{};

    return ExpansionTile(
      key: ValueKey(_schemaExpanded),
      initiallyExpanded: _schemaExpanded,
      onExpansionChanged: (v) => setState(() => _schemaExpanded = v),
      tilePadding: const EdgeInsets.symmetric(horizontal: 16),
      title: Text(
        'Column Schema (${preview.columnNames.length} columns)',
        style: TextStyle(
          color: _theme.textPrimary,
          fontSize: 13,
          fontWeight: FontWeight.w600,
        ),
      ),
      iconColor: _theme.textSecondary,
      collapsedIconColor: _theme.textSecondary,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
          child: Wrap(
            spacing: 8,
            runSpacing: 6,
            children: preview.columnNames.map((name) {
              final dtype = _inferDtype(firstRow[name]);
              return Chip(
                label: Text(
                  '$name ($dtype)',
                  style: const TextStyle(fontSize: 12),
                ),
                backgroundColor: _theme.bgSurface,
                side: BorderSide(color: _theme.dataGov, width: 0.5),
                labelStyle: TextStyle(color: _theme.textPrimary),
                padding: const EdgeInsets.symmetric(horizontal: 4),
                materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
              );
            }).toList(),
          ),
        ),
      ],
    );
  }

  Widget _buildFilterToolbar(DataPreviewResponse preview) {
    // Extract unique GEO values from the preview data for the dropdown
    final geoValues = <String>{};
    for (final row in preview.data) {
      final geo = row['GEO'];
      if (geo != null) geoValues.add(geo.toString());
    }
    final sortedGeos = geoValues.toList()..sort();

    final filter = ref.watch(previewFilterProvider);

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      decoration: BoxDecoration(
        border: Border(
          bottom: BorderSide(color: _theme.bgSurface, width: 1),
        ),
      ),
      child: Wrap(
        spacing: 12,
        runSpacing: 8,
        crossAxisAlignment: WrapCrossAlignment.center,
        children: [
          // GEO dropdown — wrapped in ConstrainedBox to prevent overflow
          ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 200),
            child: DropdownButtonFormField<String>(
              value: filter.geoFilter,
              isExpanded: true,
              decoration: InputDecoration(
                labelText: 'Geography',
                labelStyle: TextStyle(color: _theme.textSecondary, fontSize: 12),
                isDense: true,
                contentPadding:
                    const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
                border: const OutlineInputBorder(),
                enabledBorder: OutlineInputBorder(
                  borderSide: BorderSide(color: _theme.textSecondary),
                ),
              ),
              dropdownColor: _theme.bgSurface,
              style: TextStyle(color: _theme.textPrimary, fontSize: 13),
              hint: Text(
                'All geographies',
                style: TextStyle(color: _theme.textSecondary, fontSize: 13),
                overflow: TextOverflow.ellipsis,
              ),
              items: [
                const DropdownMenuItem<String>(
                  value: null,
                  child: Text('All geographies', overflow: TextOverflow.ellipsis),
                ),
                ...sortedGeos.map(
                  (g) => DropdownMenuItem(
                    value: g,
                    child: Text(g, overflow: TextOverflow.ellipsis),
                  ),
                ),
              ],
              onChanged: (value) {
                ref.read(previewFilterProvider.notifier).state =
                    filter.copyWith(geoFilter: value);
              },
            ),
          ),

          // Date from
          SizedBox(
            width: 130,
            child: TextField(
              controller: _dateFromController,
              style:
                  TextStyle(color: _theme.textPrimary, fontSize: 13),
              decoration: InputDecoration(
                labelText: 'Date from',
                labelStyle: TextStyle(color: _theme.textSecondary, fontSize: 12),
                hintText: 'YYYY-MM',
                hintStyle: TextStyle(color: _theme.textSecondary, fontSize: 12),
                isDense: true,
                contentPadding:
                    const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
                border: const OutlineInputBorder(),
                enabledBorder: OutlineInputBorder(
                  borderSide: BorderSide(color: _theme.textSecondary),
                ),
              ),
              onChanged: (value) {
                ref.read(previewFilterProvider.notifier).state =
                    filter.copyWith(dateFromFilter: value);
              },
            ),
          ),

          // Date to
          SizedBox(
            width: 130,
            child: TextField(
              controller: _dateToController,
              style:
                  TextStyle(color: _theme.textPrimary, fontSize: 13),
              decoration: InputDecoration(
                labelText: 'Date to',
                labelStyle: TextStyle(color: _theme.textSecondary, fontSize: 12),
                hintText: 'YYYY-MM',
                hintStyle: TextStyle(color: _theme.textSecondary, fontSize: 12),
                isDense: true,
                contentPadding:
                    const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
                border: const OutlineInputBorder(),
                enabledBorder: OutlineInputBorder(
                  borderSide: BorderSide(color: _theme.textSecondary),
                ),
              ),
              onChanged: (value) {
                ref.read(previewFilterProvider.notifier).state =
                    filter.copyWith(dateToFilter: value);
              },
            ),
          ),

          // Free-text search
          SizedBox(
            width: 200,
            child: TextField(
              controller: _searchController,
              style:
                  TextStyle(color: _theme.textPrimary, fontSize: 13),
              decoration: InputDecoration(
                labelText: 'Search',
                labelStyle: TextStyle(color: _theme.textSecondary, fontSize: 12),
                prefixIcon:
                    Icon(Icons.search, size: 18, color: _theme.textSecondary),
                isDense: true,
                contentPadding:
                    const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
                border: const OutlineInputBorder(),
                enabledBorder: OutlineInputBorder(
                  borderSide: BorderSide(color: _theme.textSecondary),
                ),
              ),
              onChanged: _onSearchChanged,
            ),
          ),

          // Clear filters
          TextButton.icon(
            onPressed: _clearFilters,
            icon: const Icon(Icons.clear_all, size: 18),
            label: const Text('Clear Filters'),
            style: TextButton.styleFrom(
              foregroundColor: _theme.textSecondary,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDataTable(
    List<String> columnNames,
    List<({int originalIndex, Map<String, dynamic> data})> rows,
    String? sortCol,
    bool sortAsc,
    DataPreviewResponse preview,
    CubeDiff diff,
  ) {
    // Infer dtypes from first row for numeric detection
    final firstRow =
        preview.data.isNotEmpty ? preview.data.first : <String, dynamic>{};

    return SingleChildScrollView(
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: DataTable(
          sortColumnIndex:
              sortCol != null
                  ? columnNames.indexOf(sortCol)
                  : null,
          sortAscending: sortAsc,
          headingRowColor: WidgetStateProperty.all(_theme.bgSurface),
          dataRowColor: WidgetStateProperty.resolveWith((states) {
            return null; // handled by row striping below
          }),
          columnSpacing: 24,
          columns: columnNames.map((name) {
            final sampleVal = firstRow[name];
            final isNumeric = sampleVal is num;
            return DataColumn(
              label: Text(
                name,
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  color: _theme.textPrimary,
                ),
              ),
              numeric: isNumeric,
              onSort: (_, __) => _onSort(name),
            );
          }).toList(),
          rows: List.generate(rows.length, (index) {
            final entry = rows[index];
            final row = entry.data;
            final originalIndex = entry.originalIndex;
            final isEven = index % 2 == 0;
            return DataRow(
              color: WidgetStateProperty.all(
                isEven
                    ? Colors.transparent
                    : _theme.bgSurface.withOpacity(0.5),
              ),
              cells: columnNames.map((name) {
                final value = row[name];
                final isNumeric = firstRow[name] is num;
                final highlighted = diff is ComputedCubeDiff &&
                    diff.changedCells.contains(DiffCellKey(originalIndex, name));
                return DataCell(
                  _buildCell(value, isNumeric, highlighted: highlighted),
                );
              }).toList(),
            );
          }),
        ),
      ),
    );
  }

  Widget _buildCell(dynamic value, bool isNumeric, {bool highlighted = false}) {
    final Widget cellContent;
    if (value == null) {
      cellContent = Text(
        '\u2014',
        style: TextStyle(color: _theme.textSecondary),
      );
    } else {
      final text = isNumeric ? _formatNumber(value) : value.toString();
      cellContent = Tooltip(
        message: value.toString(),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 200),
          child: Text(
            text,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(color: _theme.textPrimary, fontSize: 13),
          ),
        ),
      );
    }

    if (!highlighted) return cellContent;
    return Container(
      color: _theme.accentMuted,
      padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
      child: cellContent,
    );
  }

  String _formatNumber(dynamic value) {
    if (value is int) {
      return _formatInt(value);
    }
    if (value is double) {
      final parts = value.toStringAsFixed(2).split('.');
      final intPart = int.parse(parts[0].replaceFirst('-', ''));
      final decPart = parts[1].replaceAll(RegExp(r'0+$'), '');
      final sign = value < 0 ? '-' : '';
      if (decPart.isEmpty) return '$sign${_formatInt(intPart)}';
      return '$sign${_formatInt(intPart)}.$decPart';
    }
    return value.toString();
  }

  Widget _buildActionsBar() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        border: Border(
          top: BorderSide(color: _theme.bgSurface, width: 1),
        ),
      ),
      child: Row(
        children: [
          OutlinedButton.icon(
            onPressed: () => context.go('/cubes/search'),
            icon: const Icon(Icons.arrow_back, size: 18),
            label: const Text('Back to Search'),
            style: OutlinedButton.styleFrom(
              foregroundColor: _theme.textSecondary,
              side: BorderSide(color: _theme.textSecondary),
            ),
          ),
          const Spacer(),
          ElevatedButton.icon(
            onPressed: () {
              // Extract productId from storageKey if possible.
              final parts = widget.storageKey.split('/');
              final productId =
                  parts.length >= 2 ? parts[parts.length - 2] : null;
              context.go(
                '/graphics/config?key=${Uri.encodeComponent(widget.storageKey)}'
                '${productId != null ? '&productId=$productId' : ''}',
              );
            },
            icon: const Icon(Icons.bar_chart, size: 18),
            label: const Text('Generate Chart'),
          ),
        ],
      ),
    );
  }
}
