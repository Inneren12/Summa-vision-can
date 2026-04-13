import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_theme.dart';
import '../../data_preview/data/data_preview_repository.dart';
import '../application/cube_providers.dart';

/// Detail screen for a single cube.
///
/// Displays all metadata fields in a card layout.
/// "Fetch Data" triggers a fetch job, polls for completion, then
/// navigates to the Data Preview screen.
class CubeDetailScreen extends ConsumerStatefulWidget {
  const CubeDetailScreen({super.key, required this.productId});

  final String productId;

  @override
  ConsumerState<CubeDetailScreen> createState() => _CubeDetailScreenState();
}

class _CubeDetailScreenState extends ConsumerState<CubeDetailScreen> {
  bool _isFetching = false;
  int _pollAttempts = 0;
  static const int _maxPolls = 60;
  static const Duration _pollInterval = Duration(seconds: 2);

  SummaTheme get _theme => Theme.of(context).extension<SummaTheme>()!;

  Future<void> _onFetchData() async {
    if (_isFetching) return;

    setState(() {
      _isFetching = true;
      _pollAttempts = 0;
    });

    try {
      final repo = ref.read(dataPreviewRepositoryProvider);

      // 1. Trigger fetch
      final jobId = await repo.triggerFetch(widget.productId);

      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Fetching data... (Job: $jobId)'),
          duration: const Duration(seconds: 3),
        ),
      );

      // 2. Poll for completion
      for (var i = 0; i < _maxPolls; i++) {
        await Future.delayed(_pollInterval);
        if (!mounted) return;

        setState(() => _pollAttempts = i + 1);

        final status = await repo.getJobStatus(jobId);
        final jobStatus = (status['status'] as String?)?.toLowerCase() ?? '';

        if (jobStatus == 'success' || jobStatus == 'completed') {
          // Extract storage_key from result_json
          String? storageKey;
          final resultJson = status['result_json'];
          if (resultJson is String) {
            final parsed = json.decode(resultJson) as Map<String, dynamic>;
            storageKey = parsed['storage_key'] as String?;
          } else if (resultJson is Map) {
            storageKey = resultJson['storage_key'] as String?;
          }

          if (!mounted) return;

          if (storageKey != null) {
            context.go(
              '/data/preview?key=${Uri.encodeComponent(storageKey)}',
            );
          } else {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(
                content: Text('Fetch completed but no storage key returned'),
              ),
            );
          }

          setState(() => _isFetching = false);
          return;
        }

        if (jobStatus == 'failed') {
          if (!mounted) return;
          final errorMsg =
              status['error']?.toString() ?? 'Data fetch failed on server';
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text(errorMsg)),
          );
          setState(() => _isFetching = false);
          return;
        }
      }

      // Timeout
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: const Text('Data fetch timed out. Try again?'),
          action: SnackBarAction(
            label: 'Retry',
            onPressed: _onFetchData,
          ),
        ),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Fetch error: $e')),
      );
    } finally {
      if (mounted) setState(() => _isFetching = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final detailAsync = ref.watch(cubeDetailProvider(widget.productId));

    return Scaffold(
      appBar: AppBar(title: Text('Cube ${widget.productId}')),
      body: detailAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (err, _) => Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.error_outline,
                  color: _theme.destructive, size: 48),
              const SizedBox(height: 16),
              Text(
                'Failed to load cube\n$err',
                textAlign: TextAlign.center,
                style: TextStyle(color: _theme.textSecondary),
              ),
              const SizedBox(height: 16),
              ElevatedButton(
                onPressed: () =>
                    ref.invalidate(cubeDetailProvider(widget.productId)),
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
                    style: TextStyle(
                      color: _theme.textPrimary,
                      fontSize: 20,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  if (cube.titleFr != null) ...[
                    const SizedBox(height: 4),
                    Text(
                      cube.titleFr!,
                      style: TextStyle(
                        color: _theme.textSecondary,
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
                        '${cube.startDate ?? '\u2014'} to ${cube.endDate ?? '\u2014'}',
                  ),
                  _DetailRow(
                    label: 'Archive Status',
                    value: cube.archiveStatus ? 'Archived' : 'Active',
                  ),
                  const SizedBox(height: 24),
                  // Fetch Data button
                  ElevatedButton.icon(
                    onPressed: _isFetching ? null : _onFetchData,
                    icon: _isFetching
                        ? SizedBox(
                            width: 18,
                            height: 18,
                            child: CircularProgressIndicator(
                              strokeWidth: 2,
                              color: _theme.bgApp,
                            ),
                          )
                        : const Icon(Icons.download),
                    label: Text(
                      _isFetching
                          ? 'Fetching... ($_pollAttempts/$_maxPolls)'
                          : 'Fetch Data',
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
    final theme = Theme.of(context).extension<SummaTheme>()!;
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 130,
            child: Text(
              label,
              style: TextStyle(
                color: theme.textSecondary,
                fontWeight: FontWeight.w600,
                fontSize: 13,
              ),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: TextStyle(
                color: theme.textPrimary,
                fontSize: 14,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
