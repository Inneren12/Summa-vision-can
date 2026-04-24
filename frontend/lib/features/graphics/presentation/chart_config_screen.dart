import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_theme.dart';
import '../../../l10n/backend_errors.dart';
import '../../../l10n/generated/app_localizations.dart';
import '../../cubes/application/cube_providers.dart';
import '../application/chart_config_notifier.dart';
import '../application/generation_state_notifier.dart';
import '../data/download_helper.dart';
import '../domain/chart_constants.dart';
import '../domain/graphics_generate_request.dart';
import '../domain/raw_data_upload.dart';
import 'data_upload_widget.dart';
import 'editable_data_table.dart';

/// Which source the operator wants to generate from.
enum DataSource { statcan, upload }

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

  // Upload data source state. When [_dataSource] is [DataSource.upload]
  // the operator is generating from locally-uploaded JSON/CSV rather than
  // from a StatCan cube.
  DataSource _dataSource = DataSource.statcan;
  List<Map<String, dynamic>>? _uploadedData;
  List<RawDataColumn>? _uploadedColumns;
  String? _uploadError;

  SummaTheme get _theme => Theme.of(context).extension<SummaTheme>()!;

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
        // Cube lookup failed -- leave title empty for manual entry.
      }
    }
    if (mounted) setState(() => _initialized = true);
  }

  @override
  void dispose() {
    _titleController.dispose();
    super.dispose();
  }

  void _onGenerate(AppLocalizations l10n) {
    if (!_formKey.currentState!.validate()) return;

    final config = ref.read(chartConfigNotifierProvider);

    if (_dataSource == DataSource.upload) {
      if (_uploadedData == null ||
          _uploadedData!.isEmpty ||
          _uploadedColumns == null) {
        setState(() => _uploadError = l10n.chartConfigUploadMissingError);
        return;
      }
      setState(() => _uploadError = null);
      final request = GenerateFromDataRequest(
        data: _uploadedData!,
        columns: _uploadedColumns!,
        chartType: config.chartType.apiValue,
        title: config.title,
        size: config.sizePreset.dimensions,
        category: config.category.apiValue,
      );
      ref
          .read(chartGenerationNotifierProvider.notifier)
          .generateFromData(request);
      return;
    }

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

  /// Design system colour swatch for each background category.
  Color _categoryColor(BackgroundCategory cat) => switch (cat) {
        BackgroundCategory.housing => _theme.dataHousing,
        BackgroundCategory.inflation => _theme.dataMonopoly,
        BackgroundCategory.employment => _theme.dataPositive,
        BackgroundCategory.trade => _theme.dataSociety,
        BackgroundCategory.energy => _theme.dataWarning,
        BackgroundCategory.demographics => _theme.dataGov,
      };

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final config = ref.watch(chartConfigNotifierProvider);
    final genState = ref.watch(chartGenerationNotifierProvider);

    // Reset state if we're viewing a different StatCan dataset. In upload
    // mode ``config.dataKey`` is irrelevant — the key is created server-side
    // from the uploaded rows on each Generate click — so skip the reset.
    if (_dataSource == DataSource.statcan &&
        config.dataKey != widget.storageKey) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        ref.read(chartConfigNotifierProvider.notifier).reset(
              widget.storageKey,
              sourceProductId: widget.productId,
            );
        ref.read(chartGenerationNotifierProvider.notifier).reset();

        _titleController.clear();

        if (widget.productId != null) {
          _prepopulateTitle();
        }
      });
    }

    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.chartConfigAppBarTitle),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.go(
            '/data/preview?key=${Uri.encodeComponent(widget.storageKey)}',
          ),
        ),
      ),
      body: switch (genState.phase) {
        GenerationPhase.idle => _buildConfigForm(l10n),
        GenerationPhase.submitting => _buildSubmittingView(l10n),
        GenerationPhase.polling => _buildPollingView(l10n, genState.pollCount),
        GenerationPhase.success => _buildResultView(l10n, genState),
        GenerationPhase.failed => _buildErrorView(
            l10n,
            mapBackendErrorCode(genState.errorCode, l10n) ??
                genState.errorMessage ??
                l10n.generationStatusFailed,
            isTimeout: false,
          ),
        GenerationPhase.timeout => _buildErrorView(
            l10n,
            l10n.generationStatusTimeout,
            isTimeout: true,
          ),
      },
    );
  }

  // --- Config Form ---

  Widget _buildConfigForm(AppLocalizations l10n) {
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
            _buildDataSourceSelector(l10n),
            const SizedBox(height: 16),
            if (_dataSource == DataSource.statcan)
              _buildDatasetHeader(l10n, config)
            else
              _buildUploadSection(l10n),
            const SizedBox(height: 24),
            _buildChartTypeSelector(l10n, config),
            const SizedBox(height: 24),
            _buildSizePresetSelector(l10n, config),
            const SizedBox(height: 24),
            _buildCategorySelector(l10n, config),
            const SizedBox(height: 24),
            _buildTitleField(l10n, config),
            const SizedBox(height: 32),
            _buildGenerateButton(l10n, config),
          ],
        ),
      ),
    );
  }

  Widget _buildDataSourceSelector(AppLocalizations l10n) {
    return SegmentedButton<DataSource>(
      key: const Key('data_source_selector'),
      segments: [
        ButtonSegment(
          value: DataSource.statcan,
          label: Text(l10n.chartConfigDataSourceStatcan),
          icon: const Icon(Icons.dataset, size: 18),
        ),
        ButtonSegment(
          value: DataSource.upload,
          label: Text(l10n.chartConfigDataSourceUpload),
          icon: const Icon(Icons.upload_file, size: 18),
        ),
      ],
      selected: {_dataSource},
      onSelectionChanged: (selection) {
        setState(() => _dataSource = selection.first);
      },
    );
  }

  Widget _buildUploadSection(AppLocalizations l10n) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              l10n.chartConfigCustomDataSectionTitle,
              style: TextStyle(
                color: _theme.textSecondary,
                fontSize: 12,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 8),
            DataUploadWidget(
              onDataLoaded: (data, columns) {
                setState(() {
                  _uploadedData = List<Map<String, dynamic>>.from(data);
                  _uploadedColumns = columns;
                  _uploadError = null;
                });
              },
            ),
            if (_uploadError != null)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Text(
                  _uploadError!,
                  key: const Key('upload_data_error'),
                  style: TextStyle(color: _theme.destructive),
                ),
              ),
            if (_uploadedData != null && _uploadedColumns != null) ...[
              const SizedBox(height: 16),
              SizedBox(
                height: 400,
                child: EditableDataTable(
                  data: _uploadedData!,
                  columns: _uploadedColumns!.map((c) => c.name).toList(),
                  onCellChanged: (row, col, val) {
                    setState(() {
                      _uploadedData![row] = {
                        ..._uploadedData![row],
                        col: val,
                      };
                    });
                  },
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildDatasetHeader(AppLocalizations l10n, ChartConfig config) {
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
            Text(
              l10n.chartConfigDatasetLabel,
              style: TextStyle(
                color: _theme.textSecondary,
                fontSize: 12,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              label,
              style: TextStyle(
                color: _theme.dataGov,
                fontSize: 14,
                fontWeight: FontWeight.w600,
              ),
            ),
            if (config.sourceProductId != null) ...[
              const SizedBox(height: 2),
              Text(
                l10n.chartConfigProductIdLabel(config.sourceProductId!),
                style: TextStyle(
                  color: _theme.textSecondary,
                  fontSize: 12,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildChartTypeSelector(AppLocalizations l10n, ChartConfig config) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          l10n.editorChartTypeLabel,
          style: TextStyle(
            color: _theme.textPrimary,
            fontSize: 14,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 8),
        DropdownButtonFormField<ChartType>(
          key: const Key('chart_type_selector'),
          value: config.chartType,
          isExpanded: true,
          decoration: InputDecoration(
            border: const OutlineInputBorder(),
            enabledBorder: OutlineInputBorder(
              borderSide: BorderSide(color: _theme.textSecondary),
            ),
            contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
          ),
          dropdownColor: _theme.bgSurface,
          style: TextStyle(color: _theme.textPrimary),
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

  Widget _buildSizePresetSelector(AppLocalizations l10n, ChartConfig config) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          l10n.chartConfigSizePresetLabel,
          style: TextStyle(
            color: _theme.textPrimary,
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
                return _theme.bgApp;
              }
              return _theme.textPrimary;
            }),
            backgroundColor: WidgetStateProperty.resolveWith((states) {
              if (states.contains(WidgetState.selected)) {
                return _theme.accent;
              }
              return _theme.bgSurface;
            }),
          ),
        ),
      ],
    );
  }

  Widget _buildCategorySelector(AppLocalizations l10n, ChartConfig config) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          l10n.chartConfigBackgroundCategoryLabel,
          style: TextStyle(
            color: _theme.textPrimary,
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
              label: Text(cat.localizedLabel(l10n)),
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
              backgroundColor: _theme.bgSurface,
              labelStyle: TextStyle(
                color: isSelected
                    ? _categoryColor(cat)
                    : _theme.textPrimary,
                fontSize: 13,
              ),
              side: BorderSide(
                color: isSelected
                    ? _categoryColor(cat)
                    : _theme.textSecondary.withOpacity(0.3),
              ),
            );
          }).toList(),
        ),
      ],
    );
  }

  Widget _buildTitleField(AppLocalizations l10n, ChartConfig config) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          l10n.chartConfigHeadlineLabel,
          style: TextStyle(
            color: _theme.textPrimary,
            fontSize: 14,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 8),
        TextFormField(
          key: const Key('title_field'),
          controller: _titleController,
          style: TextStyle(color: _theme.textPrimary),
          decoration: InputDecoration(
            hintText: l10n.chartConfigHeadlineHint,
            hintStyle: TextStyle(color: _theme.textSecondary),
            border: const OutlineInputBorder(),
            enabledBorder: OutlineInputBorder(
              borderSide: BorderSide(color: _theme.textSecondary),
            ),
            counterStyle: TextStyle(color: _theme.textSecondary),
          ),
          maxLength: 200,
          validator: (value) {
            if (value == null || value.trim().isEmpty) {
              return l10n.chartConfigHeadlineRequired;
            }
            if (value.length > 200) {
              return l10n.chartConfigHeadlineMaxChars;
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

  Widget _buildGenerateButton(AppLocalizations l10n, ChartConfig config) {
    final titleMissing = config.title.trim().isEmpty;
    final uploadMissing = _dataSource == DataSource.upload &&
        (_uploadedData == null || _uploadedData!.isEmpty);
    final isDisabled = titleMissing || uploadMissing;

    return SizedBox(
      height: 52,
      child: ElevatedButton.icon(
        key: const Key('generate_button'),
        onPressed: isDisabled ? null : () => _onGenerate(l10n),
        icon: const Icon(Icons.auto_awesome, size: 20),
        label: Text(
          l10n.editorGenerateGraphicButton,
          style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
        ),
        style: ElevatedButton.styleFrom(
          disabledBackgroundColor: _theme.bgSurface,
          disabledForegroundColor: _theme.textSecondary,
        ),
      ),
    );
  }

  // --- Generation Phase Views ---

  Widget _buildSubmittingView(AppLocalizations l10n) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const CircularProgressIndicator(),
          const SizedBox(height: 16),
          Text(
            l10n.generationStatusSubmitting,
            style: TextStyle(color: _theme.textSecondary),
          ),
        ],
      ),
    );
  }

  Widget _buildPollingView(AppLocalizations l10n, int pollCount) {
    final remaining = ((ChartGenerationNotifier.maxPolls - pollCount) * 2);

    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            CircularProgressIndicator(
              value: pollCount / ChartGenerationNotifier.maxPolls,
              color: _theme.accent,
            ),
            const SizedBox(height: 16),
            Text(
              l10n.generationStatusPolling(
                pollCount,
                ChartGenerationNotifier.maxPolls,
              ),
              style: TextStyle(color: _theme.textPrimary),
            ),
            const SizedBox(height: 8),
            LinearProgressIndicator(
              value: pollCount / ChartGenerationNotifier.maxPolls,
              color: _theme.accent,
              backgroundColor: _theme.bgSurface,
            ),
            const SizedBox(height: 8),
            Text(
              l10n.chartConfigEtaRemaining(remaining),
              style: TextStyle(
                color: _theme.textSecondary,
                fontSize: 12,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildResultView(AppLocalizations l10n, ChartGenerationState genState) {
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
              errorBuilder: (_, __, ___) => SizedBox(
                height: 300,
                child: Center(
                  child: Icon(
                    Icons.broken_image,
                    color: _theme.destructive,
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
                label: Text(l10n.chartConfigPublicationChip(result.publicationId)),
                backgroundColor: _theme.bgSurface,
                labelStyle: TextStyle(
                  color: _theme.textPrimary,
                  fontSize: 12,
                ),
              ),
              const SizedBox(width: 8),
              Chip(
                label: Text(l10n.chartConfigVersionChip(result.version.toString())),
                backgroundColor: _theme.bgSurface,
                labelStyle: TextStyle(
                  color: _theme.textPrimary,
                  fontSize: 12,
                ),
              ),
              const SizedBox(width: 8),
              Chip(
                label: Text(
                  ref.read(chartConfigNotifierProvider).chartType.displayName,
                ),
                backgroundColor: _theme.dataGov.withOpacity(0.15),
                labelStyle: TextStyle(
                  color: _theme.dataGov,
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
                      SnackBar(content: Text(l10n.previewDownloadSaved(path))),
                    );
                  }
                } catch (e) {
                  if (context.mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(
                        content: Text(l10n.previewDownloadFailed(e.toString())),
                      ),
                    );
                  }
                }
              },
              icon: const Icon(Icons.download),
              label: Text(l10n.chartConfigDownloadPreviewButton),
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
              label: Text(l10n.chartConfigGenerateAnotherButton),
              style: OutlinedButton.styleFrom(
                foregroundColor: _theme.accent,
                side: BorderSide(color: _theme.accent),
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
              label: Text(l10n.chartConfigBackToPreviewButton),
              style: OutlinedButton.styleFrom(
                foregroundColor: _theme.textSecondary,
                side: BorderSide(color: _theme.textSecondary),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildErrorView(
    AppLocalizations l10n,
    String message, {
    required bool isTimeout,
  }) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              isTimeout ? Icons.timer_off : Icons.error_outline,
              color: _theme.destructive,
              size: 48,
            ),
            const SizedBox(height: 16),
            Text(
              message,
              key: const Key('error_message'),
              textAlign: TextAlign.center,
              style: TextStyle(color: _theme.textSecondary),
            ),
            const SizedBox(height: 24),
            ElevatedButton(
              key: const Key('retry_button'),
              onPressed: () {
                ref.read(chartGenerationNotifierProvider.notifier).reset();
              },
              child: Text(
                isTimeout
                    ? l10n.commonRetryVerb
                    : l10n.chartConfigTryAgainButton,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
