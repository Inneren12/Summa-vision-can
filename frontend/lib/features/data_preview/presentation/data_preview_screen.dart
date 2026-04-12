import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_theme.dart';
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
      // Toggle direction
      final asc = ref.read(previewSortAscendingProvider);
      ref.read(previewSortAscendingProvider.notifier).state = !asc;
    } else {
      ref.read(previewSortColumnProvider.notifier).state = columnName;
      ref.read(previewSortAscendingProvider.notifier).state = true;
    }
  }

  /// Extract a human-readable label from the storage key.
  /// e.g. `statcan/processed/13-10-0888-01/2024-12-15.parquet` → `13-10-0888-01 / 2024-12-15`
  String _readableKey(String key) {
    final parts = key.split('/');
    if (parts.length >= 2) {
      final file = parts.last.replaceAll('.parquet', '');
      final productId = parts.length >= 2 ? parts[parts.length - 2] : '';
      return '$productId / $file';
    }
    return key;
  }

  @override
  Widget build(BuildContext context) {
    final previewAsync = ref.watch(dataPreviewProvider);
    final filteredRows = ref.watch(filteredPreviewRowsProvider);
    final sortCol = ref.watch(previewSortColumnProvider);
    final sortAsc = ref.watch(previewSortAscendingProvider);

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
              const Icon(Icons.error_outline,
                  color: AppTheme.errorRed, size: 48),
              const SizedBox(height: 16),
              Text(
                'Failed to load preview\n$err',
                textAlign: TextAlign.center,
                style: const TextStyle(color: AppTheme.textSecondary),
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
            return const Center(
              child: Text(
                'No data to preview',
                style: TextStyle(color: AppTheme.textSecondary),
              ),
            );
          }

          return Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // A) Header / Info Bar
              _buildInfoBar(preview),

              // B) Schema Inspector
              _buildSchemaInspector(preview.columns),

              // C) Filter Controls
              _buildFilterToolbar(preview),

              // D) Data Table
              Expanded(
                child: _buildDataTable(
                  preview.columns,
                  filteredRows,
                  sortCol,
                  sortAsc,
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
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      color: AppTheme.surfaceDark,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            _readableKey(widget.storageKey),
            style: const TextStyle(
              color: AppTheme.neonBlue,
              fontSize: 14,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 4),
          Row(
            children: [
              Text(
                'Showing ${_formatInt(preview.returnedRows)} of ${_formatInt(preview.totalRows)} rows',
                style: const TextStyle(
                  color: AppTheme.textPrimary,
                  fontSize: 13,
                ),
              ),
              if (preview.totalRows > preview.returnedRows) ...[
                const SizedBox(width: 8),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                  decoration: BoxDecoration(
                    color: AppTheme.neonYellow.withOpacity(0.15),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: const Text(
                    'Preview limited to first 100 rows',
                    style: TextStyle(
                      color: AppTheme.neonYellow,
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

  Widget _buildSchemaInspector(List<ColumnSchema> columns) {
    return ExpansionTile(
      key: ValueKey(_schemaExpanded),
      initiallyExpanded: _schemaExpanded,
      onExpansionChanged: (v) => setState(() => _schemaExpanded = v),
      tilePadding: const EdgeInsets.symmetric(horizontal: 16),
      title: Text(
        'Column Schema (${columns.length} columns)',
        style: const TextStyle(
          color: AppTheme.textPrimary,
          fontSize: 13,
          fontWeight: FontWeight.w600,
        ),
      ),
      iconColor: AppTheme.textSecondary,
      collapsedIconColor: AppTheme.textSecondary,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
          child: Wrap(
            spacing: 8,
            runSpacing: 6,
            children: columns.map((col) {
              return Chip(
                label: Text(
                  '${col.name} (${col.dtype})',
                  style: const TextStyle(fontSize: 12),
                ),
                backgroundColor: AppTheme.surfaceDark,
                side: const BorderSide(color: AppTheme.neonBlue, width: 0.5),
                labelStyle: const TextStyle(color: AppTheme.textPrimary),
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
    // Extract unique GEO values from the preview rows for the dropdown
    final geoValues = <String>{};
    for (final row in preview.rows) {
      final geo = row['GEO'];
      if (geo != null) geoValues.add(geo.toString());
    }
    final sortedGeos = geoValues.toList()..sort();

    final filter = ref.watch(previewFilterProvider);

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      decoration: const BoxDecoration(
        border: Border(
          bottom: BorderSide(color: AppTheme.surfaceDark, width: 1),
        ),
      ),
      child: Wrap(
        spacing: 12,
        runSpacing: 8,
        crossAxisAlignment: WrapCrossAlignment.center,
        children: [
          // GEO dropdown
          SizedBox(
            width: 200,
            child: DropdownButtonFormField<String>(
              value: filter.geoFilter,
              decoration: const InputDecoration(
                labelText: 'Geography',
                labelStyle: TextStyle(color: AppTheme.textSecondary, fontSize: 12),
                isDense: true,
                contentPadding:
                    EdgeInsets.symmetric(horizontal: 8, vertical: 8),
                border: OutlineInputBorder(),
                enabledBorder: OutlineInputBorder(
                  borderSide: BorderSide(color: AppTheme.textSecondary),
                ),
              ),
              dropdownColor: AppTheme.surfaceDark,
              style: const TextStyle(color: AppTheme.textPrimary, fontSize: 13),
              hint: const Text(
                'All geographies',
                style: TextStyle(color: AppTheme.textSecondary, fontSize: 13),
              ),
              items: [
                const DropdownMenuItem<String>(
                  value: null,
                  child: Text('All geographies'),
                ),
                ...sortedGeos.map(
                  (g) => DropdownMenuItem(value: g, child: Text(g)),
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
                  const TextStyle(color: AppTheme.textPrimary, fontSize: 13),
              decoration: const InputDecoration(
                labelText: 'Date from',
                labelStyle: TextStyle(color: AppTheme.textSecondary, fontSize: 12),
                hintText: 'YYYY-MM',
                hintStyle: TextStyle(color: AppTheme.textSecondary, fontSize: 12),
                isDense: true,
                contentPadding:
                    EdgeInsets.symmetric(horizontal: 8, vertical: 8),
                border: OutlineInputBorder(),
                enabledBorder: OutlineInputBorder(
                  borderSide: BorderSide(color: AppTheme.textSecondary),
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
                  const TextStyle(color: AppTheme.textPrimary, fontSize: 13),
              decoration: const InputDecoration(
                labelText: 'Date to',
                labelStyle: TextStyle(color: AppTheme.textSecondary, fontSize: 12),
                hintText: 'YYYY-MM',
                hintStyle: TextStyle(color: AppTheme.textSecondary, fontSize: 12),
                isDense: true,
                contentPadding:
                    EdgeInsets.symmetric(horizontal: 8, vertical: 8),
                border: OutlineInputBorder(),
                enabledBorder: OutlineInputBorder(
                  borderSide: BorderSide(color: AppTheme.textSecondary),
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
                  const TextStyle(color: AppTheme.textPrimary, fontSize: 13),
              decoration: const InputDecoration(
                labelText: 'Search',
                labelStyle: TextStyle(color: AppTheme.textSecondary, fontSize: 12),
                prefixIcon:
                    Icon(Icons.search, size: 18, color: AppTheme.textSecondary),
                isDense: true,
                contentPadding:
                    EdgeInsets.symmetric(horizontal: 8, vertical: 8),
                border: OutlineInputBorder(),
                enabledBorder: OutlineInputBorder(
                  borderSide: BorderSide(color: AppTheme.textSecondary),
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
              foregroundColor: AppTheme.textSecondary,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDataTable(
    List<ColumnSchema> columns,
    List<Map<String, dynamic>> rows,
    String? sortCol,
    bool sortAsc,
  ) {
    return SingleChildScrollView(
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: DataTable(
          sortColumnIndex:
              sortCol != null
                  ? columns.indexWhere((c) => c.name == sortCol)
                  : null,
          sortAscending: sortAsc,
          headingRowColor: WidgetStateProperty.all(AppTheme.surfaceDark),
          dataRowColor: WidgetStateProperty.resolveWith((states) {
            return null; // handled by row striping below
          }),
          columnSpacing: 24,
          columns: columns.map((col) {
            final isNumeric =
                col.dtype.contains('float') || col.dtype.contains('int');
            return DataColumn(
              label: Text(
                col.name,
                style: const TextStyle(
                  fontWeight: FontWeight.bold,
                  color: AppTheme.textPrimary,
                ),
              ),
              numeric: isNumeric,
              onSort: (_, __) => _onSort(col.name),
            );
          }).toList(),
          rows: List.generate(rows.length, (index) {
            final row = rows[index];
            final isEven = index % 2 == 0;
            return DataRow(
              color: WidgetStateProperty.all(
                isEven
                    ? Colors.transparent
                    : AppTheme.surfaceDark.withOpacity(0.5),
              ),
              cells: columns.map((col) {
                final value = row[col.name];
                return DataCell(_buildCell(value, col.dtype));
              }).toList(),
            );
          }),
        ),
      ),
    );
  }

  Widget _buildCell(dynamic value, String dtype) {
    if (value == null) {
      return const Text(
        '\u2014', // em dash
        style: TextStyle(color: AppTheme.textSecondary),
      );
    }

    final isNumeric = dtype.contains('float') || dtype.contains('int');
    final text = isNumeric ? _formatNumber(value) : value.toString();

    return Tooltip(
      message: value.toString(),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 200),
        child: Text(
          text,
          overflow: TextOverflow.ellipsis,
          style: const TextStyle(color: AppTheme.textPrimary, fontSize: 13),
        ),
      ),
    );
  }

  String _formatNumber(dynamic value) {
    if (value is int) {
      return _formatInt(value);
    }
    if (value is double) {
      // Split into integer and decimal parts
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
      decoration: const BoxDecoration(
        border: Border(
          top: BorderSide(color: AppTheme.surfaceDark, width: 1),
        ),
      ),
      child: Row(
        children: [
          OutlinedButton.icon(
            onPressed: () => context.go('/cubes/search'),
            icon: const Icon(Icons.arrow_back, size: 18),
            label: const Text('Back to Search'),
            style: OutlinedButton.styleFrom(
              foregroundColor: AppTheme.textSecondary,
              side: const BorderSide(color: AppTheme.textSecondary),
            ),
          ),
          const Spacer(),
          ElevatedButton.icon(
            onPressed: () {
              // Stub — navigates to placeholder until C-3 is implemented
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(
                  content: Text('Chart configuration coming in C-3'),
                  duration: Duration(seconds: 2),
                ),
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
