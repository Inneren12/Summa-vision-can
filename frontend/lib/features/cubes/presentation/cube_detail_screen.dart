import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/theme/app_theme.dart';
import '../application/cube_providers.dart';

/// Stub detail screen for a single cube.
///
/// Displays all metadata fields in a card layout.
/// The "Fetch Data" button is disabled — it will be enabled in C-3.
class CubeDetailScreen extends ConsumerWidget {
  const CubeDetailScreen({super.key, required this.productId});

  final String productId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final detailAsync = ref.watch(cubeDetailProvider(productId));

    return Scaffold(
      appBar: AppBar(title: Text('Cube $productId')),
      body: detailAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (err, _) => Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.error_outline,
                  color: AppTheme.errorRed, size: 48),
              const SizedBox(height: 16),
              Text(
                'Failed to load cube\n$err',
                textAlign: TextAlign.center,
                style: const TextStyle(color: AppTheme.textSecondary),
              ),
              const SizedBox(height: 16),
              ElevatedButton(
                onPressed: () =>
                    ref.invalidate(cubeDetailProvider(productId)),
                child: const Text('Retry'),
              ),
            ],
          ),
        ),
        data: (cube) => SingleChildScrollView(
          padding: const EdgeInsets.all(16),
          child: Card(
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Title EN
                  Text(
                    cube.titleEn,
                    style: const TextStyle(
                      color: AppTheme.textPrimary,
                      fontSize: 20,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  if (cube.titleFr != null) ...[
                    const SizedBox(height: 4),
                    Text(
                      cube.titleFr!,
                      style: const TextStyle(
                        color: AppTheme.textSecondary,
                        fontSize: 16,
                        fontStyle: FontStyle.italic,
                      ),
                    ),
                  ],
                  const Divider(height: 32),
                  _DetailRow(label: 'Product ID', value: cube.productId),
                  _DetailRow(label: 'Subject', value: cube.subjectEn),
                  _DetailRow(
                      label: 'Subject Code', value: cube.subjectCode),
                  if (cube.surveyEn != null)
                    _DetailRow(label: 'Survey', value: cube.surveyEn!),
                  _DetailRow(label: 'Frequency', value: cube.frequency),
                  _DetailRow(
                    label: 'Date Range',
                    value:
                        '${cube.startDate ?? '—'} to ${cube.endDate ?? '—'}',
                  ),
                  _DetailRow(
                    label: 'Archive Status',
                    value: cube.archiveStatus ? 'Archived' : 'Active',
                  ),
                  const SizedBox(height: 24),
                  // Disabled Fetch Data button — placeholder for C-3
                  Tooltip(
                    message: 'Coming in C-3',
                    child: ElevatedButton.icon(
                      onPressed: null,
                      icon: const Icon(Icons.download),
                      label: const Text('Fetch Data'),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _DetailRow extends StatelessWidget {
  const _DetailRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 130,
            child: Text(
              label,
              style: const TextStyle(
                color: AppTheme.textSecondary,
                fontWeight: FontWeight.w600,
                fontSize: 13,
              ),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: const TextStyle(
                color: AppTheme.textPrimary,
                fontSize: 14,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
