import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_theme.dart';
import '../../cubes/application/cube_providers.dart';
import '../application/chart_config_notifier.dart';
import '../application/generation_state_notifier.dart';
import '../data/download_helper.dart';
import '../domain/chart_constants.dart';
import '../domain/graphics_generate_request.dart';

/// Chart Configuration & Generation Screen (C-3).
///
/// The operator configures chart type, size preset, background category,
/// and headline, then triggers async generation via the B-4 pipeline.
class ChartConfigScreen extends ConsumerStatefulWidget {
  const ChartConfigScreen({
    super.key,
    required this.storageKey,
    this.productId,
  });

  final String storageKey;
  final String? productId;

  @override
  ConsumerState<ChartConfigScreen> createState() => _ChartConfigScreenState();
}

class _ChartConfigScreenState extends ConsumerState<ChartConfigScreen> {
  final _titleController = TextEditingController();
  final _formKey = GlobalKey<FormState>();
  bool _initialized = false;

  @override
  void initState() {
    super.initState();
    Future.microtask(() {
      final notifier = ref.read(chartConfigNotifierProvider.notifier);
      notifier.setDataKey(widget.storageKey, productId: widget.productId);
      _prepopulateTitle();
    });
  }

  Future<void> _prepopulateTitle() async {
    if (widget.productId != null && widget.productId!.isNotEmpty) {
      try {
        final cube =
            await ref.read(cubeDetailProvider(widget.productId!).future);
        final config = ref.read(chartConfigNotifierProvider);
        if (config.title.isEmpty && mounted) {
          ref.read(chartConfigNotifierProvider.notifier).setTitle(cube.titleEn);
          _titleController.text = cube.titleEn;
        }
      } catch (_) {
        // Cube lookup failed — leave title empty for manual entry.
      }
    }
    if (mounted) setState(() => _initialized = true);
  }

  @override
  void dispose() {
    _titleController.dispose();
    super.dispose();
  }

  void _onGenerate() {
    if (!_formKey.currentState!.validate()) return;

    final config = ref.read(chartConfigNotifierProvider);
    final request = GraphicsGenerateRequest(
      dataKey: config.dataKey,
      chartType: config.chartType.apiValue,
      title: config.title,
      size: config.sizePreset.dimensions,
      category: config.category.apiValue,
      sourceProductId: config.sourceProductId,
    );
    ref.read(chartGenerationNotifierProvider.notifier).generate(request);
  }

  /// Neon colour swatch for each background category (from B-2 palette).
  Color _categoryColor(BackgroundCategory cat) => switch (cat) {
        BackgroundCategory.housing => const Color(0xFF00E5FF), // cyan
        BackgroundCategory.inflation => const Color(0xFFFF6E40), // red-orange
        BackgroundCategory.employment => AppTheme.neonGreen,
        BackgroundCategory.trade => const Color(0xFFBB86FC), // purple
        BackgroundCategory.energy => AppTheme.neonYellow,
        BackgroundCategory.demographics => AppTheme.neonBlue,
      };

  @override
  Widget build(BuildContext context) {
    final config = ref.watch(chartConfigNotifierProvider);
    final genState = ref.watch(chartGenerationNotifierProvider);

    // Reset state if we're viewing a different dataset
    if (config.dataKey != widget.storageKey) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        ref.read(chartConfigNotifierProvider.notifier).reset(
              widget.storageKey,
              sourceProductId: widget.productId,
            );
        ref.read(chartGenerationNotifierProvider.notifier).reset();
      });
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text('Chart Configuration'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.go(
            '/data/preview?key=${Uri.encodeComponent(widget.storageKey)}',
          ),
        ),
      ),
      body: switch (genState.phase) {
        GenerationPhase.idle => _buildConfigForm(),
        GenerationPhase.submitting => _buildSubmittingView(),
        GenerationPhase.polling => _buildPollingView(genState.pollCount),
        GenerationPhase.success => _buildResultView(genState),
        GenerationPhase.failed => _buildErrorView(
            genState.errorMessage ?? 'Generation failed.',
          ),
        GenerationPhase.timeout => _buildErrorView(
            'Generation timed out after 2 minutes.',
          ),
      },
    );
  }

  // ─── Config Form ─────────────────────────────────────────────────

  Widget _buildConfigForm() {
    final config = ref.watch(chartConfigNotifierProvider);

    if (!_initialized) {
      return const Center(child: CircularProgressIndicator());
    }

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Form(
        key: _formKey,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // A) Dataset info (read-only)
            _buildDatasetHeader(config),
            const SizedBox(height: 24),

            // B) Chart type selector
            _buildChartTypeSelector(config),
            const SizedBox(height: 24),

            // C) Size preset selector
            _buildSizePresetSelector(config),
            const SizedBox(height: 24),

            // D) Background category selector
            _buildCategorySelector(config),
            const SizedBox(height: 24),

            // E) Title input
            _buildTitleField(config),
            const SizedBox(height: 32),

            // F) Generate button
            _buildGenerateButton(config),
          ],
        ),
      ),
    );
  }

  Widget _buildDatasetHeader(ChartConfig config) {
    final parts = config.dataKey.split('/');
    String label = config.dataKey;
    if (parts.length >= 2) {
      final productId = parts[parts.length - 2];
      final file = parts.last.replaceAll('.parquet', '');
      label = '$productId / $file';
    }

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Dataset',
              style: TextStyle(
                color: AppTheme.textSecondary,
                fontSize: 12,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              label,
              style: const TextStyle(
                color: AppTheme.neonBlue,
                fontSize: 14,
                fontWeight: FontWeight.w600,
              ),
            ),
            if (config.sourceProductId != null) ...[
              const SizedBox(height: 2),
              Text(
                'Product ID: ${config.sourceProductId}',
                style: const TextStyle(
                  color: AppTheme.textSecondary,
                  fontSize: 12,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildChartTypeSelector(ChartConfig config) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Chart Type',
          style: TextStyle(
            color: AppTheme.textPrimary,
            fontSize: 14,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 8),
        DropdownButtonFormField<ChartType>(
          key: const Key('chart_type_selector'),
          value: config.chartType,
          isExpanded: true,
          decoration: const InputDecoration(
            border: OutlineInputBorder(),
            enabledBorder: OutlineInputBorder(
              borderSide: BorderSide(color: AppTheme.textSecondary),
            ),
            contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 12),
          ),
          dropdownColor: AppTheme.surfaceDark,
          style: const TextStyle(color: AppTheme.textPrimary),
          items: ChartType.values
              .map(
                (t) => DropdownMenuItem(
                  value: t,
                  child: Text(t.displayName),
                ),
              )
              .toList(),
          onChanged: (value) {
            if (value != null) {
              ref.read(chartConfigNotifierProvider.notifier).setChartType(value);
            }
          },
        ),
      ],
    );
  }

  Widget _buildSizePresetSelector(ChartConfig config) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Size Preset',
          style: TextStyle(
            color: AppTheme.textPrimary,
            fontSize: 14,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 8),
        SegmentedButton<SizePreset>(
          key: const Key('size_preset_selector'),
          segments: SizePreset.values
              .map(
                (p) => ButtonSegment(
                  value: p,
                  label: Text(
                    p.displayName,
                    style: const TextStyle(fontSize: 12),
                  ),
                ),
              )
              .toList(),
          selected: {config.sizePreset},
          onSelectionChanged: (selected) {
            ref
                .read(chartConfigNotifierProvider.notifier)
                .setSizePreset(selected.first);
          },
          style: ButtonStyle(
            foregroundColor: WidgetStateProperty.resolveWith((states) {
              if (states.contains(WidgetState.selected)) {
                return AppTheme.backgroundDark;
              }
              return AppTheme.textPrimary;
            }),
            backgroundColor: WidgetStateProperty.resolveWith((states) {
              if (states.contains(WidgetState.selected)) {
                return AppTheme.neonGreen;
              }
              return AppTheme.surfaceDark;
            }),
          ),
        ),
      ],
    );
  }

  Widget _buildCategorySelector(ChartConfig config) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Background Category',
          style: TextStyle(
            color: AppTheme.textPrimary,
            fontSize: 14,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: BackgroundCategory.values.map((cat) {
            final isSelected = config.category == cat;
            return ChoiceChip(
              key: Key('category_chip_${cat.apiValue}'),
              label: Text(cat.displayName),
              avatar: CircleAvatar(
                backgroundColor: _categoryColor(cat),
                radius: 8,
              ),
              selected: isSelected,
              onSelected: (_) {
                ref
                    .read(chartConfigNotifierProvider.notifier)
                    .setCategory(cat);
              },
              selectedColor: _categoryColor(cat).withOpacity(0.25),
              backgroundColor: AppTheme.surfaceDark,
              labelStyle: TextStyle(
                color: isSelected
                    ? _categoryColor(cat)
                    : AppTheme.textPrimary,
                fontSize: 13,
              ),
              side: BorderSide(
                color: isSelected
                    ? _categoryColor(cat)
                    : AppTheme.textSecondary.withOpacity(0.3),
              ),
            );
          }).toList(),
        ),
      ],
    );
  }

  Widget _buildTitleField(ChartConfig config) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Chart Headline',
          style: TextStyle(
            color: AppTheme.textPrimary,
            fontSize: 14,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 8),
        TextFormField(
          key: const Key('title_field'),
          controller: _titleController,
          style: const TextStyle(color: AppTheme.textPrimary),
          decoration: const InputDecoration(
            hintText: 'Enter chart headline...',
            hintStyle: TextStyle(color: AppTheme.textSecondary),
            border: OutlineInputBorder(),
            enabledBorder: OutlineInputBorder(
              borderSide: BorderSide(color: AppTheme.textSecondary),
            ),
            counterStyle: TextStyle(color: AppTheme.textSecondary),
          ),
          maxLength: 200,
          validator: (value) {
            if (value == null || value.trim().isEmpty) {
              return 'Headline is required';
            }
            if (value.length > 200) {
              return 'Maximum 200 characters';
            }
            return null;
          },
          onChanged: (value) {
            ref.read(chartConfigNotifierProvider.notifier).setTitle(value);
          },
        ),
      ],
    );
  }

  Widget _buildGenerateButton(ChartConfig config) {
    final isDisabled = config.title.trim().isEmpty;

    return SizedBox(
      height: 52,
      child: ElevatedButton.icon(
        key: const Key('generate_button'),
        onPressed: isDisabled ? null : _onGenerate,
        icon: const Icon(Icons.auto_awesome, size: 20),
        label: const Text(
          'Generate Graphic',
          style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
        ),
        style: ElevatedButton.styleFrom(
          disabledBackgroundColor: AppTheme.surfaceDark,
          disabledForegroundColor: AppTheme.textSecondary,
        ),
      ),
    );
  }

  // ─── Generation Phase Views ──────────────────────────────────────

  Widget _buildSubmittingView() {
    return const Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          CircularProgressIndicator(),
          SizedBox(height: 16),
          Text(
            'Submitting generation task...',
            style: TextStyle(color: AppTheme.textSecondary),
          ),
        ],
      ),
    );
  }

  Widget _buildPollingView(int pollCount) {
    final remaining = ((ChartGenerationNotifier.maxPolls - pollCount) * 2);

    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            CircularProgressIndicator(
              value: pollCount / ChartGenerationNotifier.maxPolls,
              color: AppTheme.neonGreen,
            ),
            const SizedBox(height: 16),
            Text(
              'Generating... (poll $pollCount/${ChartGenerationNotifier.maxPolls})',
              style: const TextStyle(color: AppTheme.textPrimary),
            ),
            const SizedBox(height: 8),
            LinearProgressIndicator(
              value: pollCount / ChartGenerationNotifier.maxPolls,
              color: AppTheme.neonGreen,
              backgroundColor: AppTheme.surfaceDark,
            ),
            const SizedBox(height: 8),
            Text(
              'Estimated time remaining: ~${remaining}s',
              style: const TextStyle(
                color: AppTheme.textSecondary,
                fontSize: 12,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildResultView(ChartGenerationState genState) {
    final result = genState.result!;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        children: [
          // Image preview
          Card(
            clipBehavior: Clip.antiAlias,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(12),
            ),
            child: Image.network(
              result.cdnUrlLowres,
              fit: BoxFit.contain,
              width: double.infinity,
              loadingBuilder: (_, child, progress) {
                if (progress == null) return child;
                return const SizedBox(
                  height: 300,
                  child: Center(child: CircularProgressIndicator()),
                );
              },
              errorBuilder: (_, __, ___) => const SizedBox(
                height: 300,
                child: Center(
                  child: Icon(
                    Icons.broken_image,
                    color: AppTheme.errorRed,
                    size: 64,
                  ),
                ),
              ),
            ),
          ),
          const SizedBox(height: 16),

          // Metadata badges
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Chip(
                label: Text('Publication #${result.publicationId}'),
                backgroundColor: AppTheme.surfaceDark,
                labelStyle: const TextStyle(
                  color: AppTheme.textPrimary,
                  fontSize: 12,
                ),
              ),
              const SizedBox(width: 8),
              Chip(
                label: Text('v${result.version}'),
                backgroundColor: AppTheme.surfaceDark,
                labelStyle: const TextStyle(
                  color: AppTheme.textPrimary,
                  fontSize: 12,
                ),
              ),
              const SizedBox(width: 8),
              Chip(
                label: Text(
                  ref.read(chartConfigNotifierProvider).chartType.displayName,
                ),
                backgroundColor: AppTheme.neonBlue.withOpacity(0.15),
                labelStyle: const TextStyle(
                  color: AppTheme.neonBlue,
                  fontSize: 12,
                ),
              ),
            ],
          ),
          const SizedBox(height: 24),

          // Action buttons
          SizedBox(
            width: double.infinity,
            height: 48,
            child: ElevatedButton.icon(
              key: const Key('download_button'),
              onPressed: () async {
                try {
                  final path =
                      await downloadAndSaveImage(result.cdnUrlLowres);
                  if (context.mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(content: Text('Saved: $path')),
                    );
                  }
                } catch (e) {
                  if (context.mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(content: Text('Download failed: $e')),
                    );
                  }
                }
              },
              icon: const Icon(Icons.download),
              label: const Text('Download Preview'),
            ),
          ),
          const SizedBox(height: 12),
          SizedBox(
            width: double.infinity,
            height: 48,
            child: OutlinedButton.icon(
              key: const Key('generate_another_button'),
              onPressed: () {
                ref.read(chartGenerationNotifierProvider.notifier).reset();
              },
              icon: const Icon(Icons.refresh, size: 18),
              label: const Text('Generate Another'),
              style: OutlinedButton.styleFrom(
                foregroundColor: AppTheme.neonGreen,
                side: const BorderSide(color: AppTheme.neonGreen),
              ),
            ),
          ),
          const SizedBox(height: 12),
          SizedBox(
            width: double.infinity,
            height: 48,
            child: OutlinedButton.icon(
              key: const Key('back_to_preview_button'),
              onPressed: () => context.go(
                '/data/preview?key=${Uri.encodeComponent(widget.storageKey)}',
              ),
              icon: const Icon(Icons.arrow_back, size: 18),
              label: const Text('Back to Preview'),
              style: OutlinedButton.styleFrom(
                foregroundColor: AppTheme.textSecondary,
                side: const BorderSide(color: AppTheme.textSecondary),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildErrorView(String message) {
    final isTimed = message.contains('timed out');

    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              isTimed ? Icons.timer_off : Icons.error_outline,
              color: AppTheme.errorRed,
              size: 48,
            ),
            const SizedBox(height: 16),
            Text(
              message,
              key: const Key('error_message'),
              textAlign: TextAlign.center,
              style: const TextStyle(color: AppTheme.textSecondary),
            ),
            const SizedBox(height: 24),
            ElevatedButton(
              key: const Key('retry_button'),
              onPressed: () {
                ref.read(chartGenerationNotifierProvider.notifier).reset();
              },
              child: Text(isTimed ? 'Retry' : 'Try Again'),
            ),
          ],
        ),
      ),
    );
  }
}
