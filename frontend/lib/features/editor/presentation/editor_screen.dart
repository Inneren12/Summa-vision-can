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
            style: const TextStyle(color: AppTheme.errorRed),
          ),
        ),
      ),
      data: (briefs) {
        final brief = briefs.where((b) => b.id == id).firstOrNull;
        if (brief == null) {
          return Scaffold(
            appBar: AppBar(title: const Text('Editor')),
            body: const Center(
              child: Text(
                'Brief not found',
                style: TextStyle(color: AppTheme.textSecondary),
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
                  child: const Text(
                    'Reset',
                    style: TextStyle(color: AppTheme.neonPink),
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
                              ? AppTheme.neonGreen
                              : AppTheme.neonYellow,
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
                        style: const TextStyle(color: AppTheme.textPrimary),
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
                        style: const TextStyle(color: AppTheme.textPrimary),
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
                        dropdownColor: AppTheme.surfaceDark,
                        style: const TextStyle(color: AppTheme.textPrimary),
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

                      // Preview Background — stub for future use
                      OutlinedButton.icon(
                        key: const Key('preview_background_btn'),
                        onPressed: null, // stub — not implemented yet
                        icon: const Icon(Icons.image_outlined),
                        label: const Text('Preview Background'),
                        style: OutlinedButton.styleFrom(
                          foregroundColor: AppTheme.textSecondary,
                          side: const BorderSide(color: AppTheme.surfaceDark),
                        ),
                      ),
                      const SizedBox(height: 16),

                      // Generate button — navigates to preview
                      SizedBox(
                        width: double.infinity,
                        child: ElevatedButton.icon(
                          key: const Key('generate_btn'),
                          onPressed: () {
                            // Navigate to preview — PR-24 will wire up actual generation
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
        hintStyle: const TextStyle(color: AppTheme.textSecondary),
        filled: true,
        fillColor: AppTheme.surfaceDark,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
          borderSide: BorderSide.none,
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
          borderSide: const BorderSide(color: AppTheme.neonGreen),
        ),
        counterStyle: const TextStyle(color: AppTheme.textSecondary),
      );
}

class _SectionLabel extends StatelessWidget {
  final String text;
  const _SectionLabel(this.text);

  @override
  Widget build(BuildContext context) {
    return Text(
      text,
      style: const TextStyle(
        color: AppTheme.textSecondary,
        fontSize: 12,
        fontWeight: FontWeight.w600,
        letterSpacing: 0.8,
      ),
    );
  }
}
