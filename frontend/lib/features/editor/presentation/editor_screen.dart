import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/theme/app_theme.dart';
import '../../queue/data/queue_repository.dart';
import '../domain/editor_notifier.dart';
import '../domain/editor_state.dart';

class EditorScreen extends ConsumerStatefulWidget {
  final String briefId;

  const EditorScreen({super.key, required this.briefId});

  @override
  ConsumerState<EditorScreen> createState() => _EditorScreenState();
}

class _EditorScreenState extends ConsumerState<EditorScreen> {
  late final TextEditingController _headlineController;
  late final TextEditingController _bgPromptController;

  SummaTheme get _theme => Theme.of(context).extension<SummaTheme>()!;

  @override
  void initState() {
    super.initState();
    _headlineController = TextEditingController();
    _bgPromptController = TextEditingController();
  }

  @override
  void dispose() {
    _headlineController.dispose();
    _bgPromptController.dispose();
    super.dispose();
  }

  void _syncControllersFromState(EditorState state) {
    if (_headlineController.text != state.headline) {
      _headlineController.text = state.headline;
    }
    if (_bgPromptController.text != state.bgPrompt) {
      _bgPromptController.text = state.bgPrompt;
    }
  }

  @override
  Widget build(BuildContext context) {
    final id = int.tryParse(widget.briefId) ?? 0;
    final queueAsync = ref.watch(queueProvider);

    return queueAsync.when(
      loading: () => const Scaffold(
        body: Center(child: CircularProgressIndicator()),
      ),
      error: (err, _) => Scaffold(
        appBar: AppBar(title: const Text('Editor')),
        body: Center(
          child: Text(
            'Failed to load brief: $err',
            style: TextStyle(color: _theme.destructive),
          ),
        ),
      ),
      data: (briefs) {
        final brief = briefs.where((b) => b.id == id).firstOrNull;
        if (brief == null) {
          return Scaffold(
            appBar: AppBar(title: const Text('Editor')),
            body: Center(
              child: Text(
                'Brief not found',
                style: TextStyle(color: _theme.textSecondary),
              ),
            ),
          );
        }

        // Initialise notifier from brief (idempotent)
        WidgetsBinding.instance.addPostFrameCallback((_) {
          ref.read(editorNotifierProvider.notifier).initFromBrief(brief);
        });

        final editorState = ref.watch(editorNotifierProvider);
        if (editorState != null) {
          _syncControllersFromState(editorState);
        }

        return Scaffold(
          appBar: AppBar(
            title: Text('Edit Brief #${brief.id}'),
            actions: [
              if (editorState?.isDirty == true)
                TextButton(
                  onPressed: () {
                    ref.read(editorNotifierProvider.notifier).reset(brief);
                    _headlineController.text = brief.headline;
                    _bgPromptController.text = '';
                  },
                  child: Text(
                    'Reset',
                    style: TextStyle(color: _theme.destructive),
                  ),
                ),
            ],
          ),
          body: editorState == null
              ? const Center(child: CircularProgressIndicator())
              : SingleChildScrollView(
                  padding: const EdgeInsets.all(24),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Virality score display (read-only)
                      _SectionLabel('Virality Score'),
                      const SizedBox(height: 8),
                      Text(
                        brief.viralityScore.toStringAsFixed(1),
                        style: TextStyle(
                          color: brief.viralityScore > 8
                              ? _theme.dataPositive
                              : _theme.dataWarning,
                          fontSize: 28,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: 24),

                      // Headline field
                      _SectionLabel('Headline'),
                      const SizedBox(height: 8),
                      TextFormField(
                        key: const Key('headline_field'),
                        controller: _headlineController,
                        style: TextStyle(color: _theme.textPrimary),
                        maxLength: 280,
                        decoration: _inputDecoration('Enter headline...'),
                        onChanged: (v) => ref
                            .read(editorNotifierProvider.notifier)
                            .updateHeadline(v),
                      ),
                      const SizedBox(height: 24),

                      // Background prompt field
                      _SectionLabel('Background Prompt'),
                      const SizedBox(height: 8),
                      TextFormField(
                        key: const Key('bg_prompt_field'),
                        controller: _bgPromptController,
                        style: TextStyle(color: _theme.textPrimary),
                        maxLines: 3,
                        decoration: _inputDecoration(
                          'Describe the AI background image...',
                        ),
                        onChanged: (v) => ref
                            .read(editorNotifierProvider.notifier)
                            .updateBgPrompt(v),
                      ),
                      const SizedBox(height: 24),

                      // Chart type dropdown
                      _SectionLabel('Chart Type'),
                      const SizedBox(height: 8),
                      DropdownButtonFormField<ChartType>(
                        key: const Key('chart_type_dropdown'),
                        value: editorState.chartType,
                        dropdownColor: _theme.bgSurface,
                        style: TextStyle(color: _theme.textPrimary),
                        decoration: _inputDecoration(''),
                        items: ChartType.values
                            .map(
                              (ct) => DropdownMenuItem(
                                value: ct,
                                child: Text(ct.displayName),
                              ),
                            )
                            .toList(),
                        onChanged: (v) {
                          if (v != null) {
                            ref
                                .read(editorNotifierProvider.notifier)
                                .updateChartType(v);
                          }
                        },
                      ),
                      const SizedBox(height: 32),

                      // Preview Background -- stub for future use
                      OutlinedButton.icon(
                        key: const Key('preview_background_btn'),
                        onPressed: null,
                        icon: const Icon(Icons.image_outlined),
                        label: const Text('Preview Background'),
                        style: OutlinedButton.styleFrom(
                          foregroundColor: _theme.textSecondary,
                          side: BorderSide(color: _theme.borderDefault),
                        ),
                      ),
                      const SizedBox(height: 16),

                      // Generate button
                      SizedBox(
                        width: double.infinity,
                        child: ElevatedButton.icon(
                          key: const Key('generate_btn'),
                          onPressed: () {
                            context.go('/preview/${brief.id}');
                          },
                          icon: const Icon(Icons.auto_awesome),
                          label: const Text('Generate Graphic'),
                        ),
                      ),
                    ],
                  ),
                ),
        );
      },
    );
  }

  InputDecoration _inputDecoration(String hint) => InputDecoration(
        hintText: hint,
        hintStyle: TextStyle(color: _theme.textSecondary),
        filled: true,
        fillColor: _theme.bgSurface,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
          borderSide: BorderSide.none,
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
          borderSide: BorderSide(color: _theme.accent),
        ),
        counterStyle: TextStyle(color: _theme.textSecondary),
      );
}

class _SectionLabel extends StatelessWidget {
  final String text;
  const _SectionLabel(this.text);

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context).extension<SummaTheme>()!;
    return Text(
      text,
      style: TextStyle(
        color: theme.textSecondary,
        fontSize: 12,
        fontWeight: FontWeight.w600,
        letterSpacing: 0.8,
      ),
    );
  }
}
