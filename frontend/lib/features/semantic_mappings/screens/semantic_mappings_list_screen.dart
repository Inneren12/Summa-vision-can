import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/routing/app_drawer.dart';
import '../models/semantic_mapping.dart';
import '../providers/semantic_mappings_providers.dart';

/// Phase 3.1b admin list screen — DataTable view (chosen because the
/// locked column count is 6 + actions = 7 effective columns, which fits
/// the tabular pattern better than a card list).
class SemanticMappingsListScreen extends ConsumerWidget {
  const SemanticMappingsListScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final asyncPage = ref.watch(semanticMappingsListProvider);

    return Scaffold(
      drawer: const AppDrawer(),
      appBar: AppBar(
        title: const Text('Semantic mappings'),
        actions: [
          IconButton(
            tooltip: 'New mapping',
            icon: const Icon(Icons.add),
            onPressed: () => context.go('/semantic-mappings/new'),
          ),
        ],
      ),
      body: Column(
        children: [
          const _FilterBar(),
          Expanded(
            child: asyncPage.when(
              data: (page) {
                if (page.items.isEmpty) {
                  return const Center(child: Text('No mappings.'));
                }
                return SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: SingleChildScrollView(
                    child: _MappingsTable(items: page.items),
                  ),
                );
              },
              loading: () =>
                  const Center(child: CircularProgressIndicator()),
              error: (e, _) => Center(child: Text('Error: $e')),
            ),
          ),
        ],
      ),
    );
  }
}

class _FilterBar extends ConsumerStatefulWidget {
  const _FilterBar();

  @override
  ConsumerState<_FilterBar> createState() => _FilterBarState();
}

class _FilterBarState extends ConsumerState<_FilterBar> {
  late final TextEditingController _cubeIdCtrl;
  late final TextEditingController _semanticKeyCtrl;

  @override
  void initState() {
    super.initState();
    final filter = ref.read(semanticMappingsFilterProvider);
    _cubeIdCtrl = TextEditingController(text: filter.cubeId ?? '');
    _semanticKeyCtrl =
        TextEditingController(text: filter.semanticKey ?? '');
  }

  @override
  void dispose() {
    _cubeIdCtrl.dispose();
    _semanticKeyCtrl.dispose();
    super.dispose();
  }

  void _apply() {
    ref.read(semanticMappingsFilterProvider.notifier).update(
          (current) => current.copyWith(
            cubeId: _cubeIdCtrl.text.trim(),
            semanticKey: _semanticKeyCtrl.text.trim(),
            offset: 0,
          ),
        );
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(8),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              key: const ValueKey('filter-cube-id'),
              controller: _cubeIdCtrl,
              decoration: const InputDecoration(
                labelText: 'cube_id',
                isDense: true,
                border: OutlineInputBorder(),
              ),
              onSubmitted: (_) => _apply(),
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: TextField(
              key: const ValueKey('filter-semantic-key'),
              controller: _semanticKeyCtrl,
              decoration: const InputDecoration(
                labelText: 'semantic_key',
                isDense: true,
                border: OutlineInputBorder(),
              ),
              onSubmitted: (_) => _apply(),
            ),
          ),
          const SizedBox(width: 8),
          FilledButton(
            key: const ValueKey('filter-apply'),
            onPressed: _apply,
            child: const Text('Filter'),
          ),
        ],
      ),
    );
  }
}

class _MappingsTable extends StatelessWidget {
  const _MappingsTable({required this.items});

  final List<SemanticMapping> items;

  @override
  Widget build(BuildContext context) {
    return DataTable(
      key: const ValueKey('semantic-mappings-table'),
      columns: const [
        DataColumn(label: Text('cube_id')),
        DataColumn(label: Text('semantic_key')),
        DataColumn(label: Text('label')),
        DataColumn(label: Text('active')),
        DataColumn(label: Text('version')),
        DataColumn(label: Text('updated_at')),
        DataColumn(label: Text('')),
      ],
      rows: [
        for (final m in items)
          DataRow(
            key: ValueKey('row-${m.id}'),
            cells: [
              DataCell(Text(m.cubeId)),
              DataCell(Text(m.semanticKey)),
              DataCell(Text(m.label)),
              DataCell(Icon(m.isActive ? Icons.check : Icons.close)),
              DataCell(Text(m.version.toString())),
              DataCell(Text(m.updatedAt.toIso8601String().split('T').first)),
              DataCell(
                Builder(
                  builder: (context) => IconButton(
                    tooltip: 'Edit',
                    icon: const Icon(Icons.edit),
                    onPressed: () =>
                        context.go('/semantic-mappings/${m.id}'),
                  ),
                ),
              ),
            ],
          ),
      ],
    );
  }
}
