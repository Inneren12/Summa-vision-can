import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/network/backend_error_envelope.dart';
import '../models/semantic_mapping.dart';
import '../providers/semantic_mappings_providers.dart';
import '../widgets/dimension_filters_editor.dart';
import '../widgets/version_conflict_modal.dart';

/// Phase 3.1b admin create/edit form for a semantic mapping.
///
/// On submit:
/// * 200/201 → snackbar + back to list.
/// * 400 envelope → inline per-field errors derived from
///   ``details.errors[].dimension_name`` / ``member_name``.
/// * 412 ``VERSION_CONFLICT`` → [VersionConflictModal] with reload.
class SemanticMappingFormScreen extends ConsumerStatefulWidget {
  const SemanticMappingFormScreen({super.key, required this.mappingId});

  /// ``null`` for create flow; otherwise the row id to edit.
  final int? mappingId;

  @override
  ConsumerState<SemanticMappingFormScreen> createState() =>
      _SemanticMappingFormScreenState();
}

class _SemanticMappingFormScreenState
    extends ConsumerState<SemanticMappingFormScreen> {
  final _formKey = GlobalKey<FormState>();

  final _cubeIdCtrl = TextEditingController();
  final _productIdCtrl = TextEditingController();
  final _semanticKeyCtrl = TextEditingController();
  final _labelCtrl = TextEditingController();
  final _descriptionCtrl = TextEditingController();
  final _measureCtrl = TextEditingController(text: 'Value');
  final _unitCtrl = TextEditingController(text: 'index');
  final _frequencyCtrl = TextEditingController(text: 'monthly');
  final _defaultGeoCtrl = TextEditingController();

  Map<String, String> _dimensionFilters = <String, String>{};
  bool _isActive = true;
  int? _ifMatchVersion;

  bool _hydrated = false;
  bool _saving = false;
  String? _formError;
  Map<String, String> _dimensionErrors = const {};

  bool get _isEdit => widget.mappingId != null;

  @override
  void dispose() {
    _cubeIdCtrl.dispose();
    _productIdCtrl.dispose();
    _semanticKeyCtrl.dispose();
    _labelCtrl.dispose();
    _descriptionCtrl.dispose();
    _measureCtrl.dispose();
    _unitCtrl.dispose();
    _frequencyCtrl.dispose();
    _defaultGeoCtrl.dispose();
    super.dispose();
  }

  void _hydrateFrom(SemanticMapping m) {
    if (_hydrated) return;
    _hydrated = true;
    _cubeIdCtrl.text = m.cubeId;
    _semanticKeyCtrl.text = m.semanticKey;
    _labelCtrl.text = m.label;
    _descriptionCtrl.text = m.description ?? '';
    _measureCtrl.text = m.config.measure;
    _unitCtrl.text = m.config.unit;
    _frequencyCtrl.text = m.config.frequency;
    _defaultGeoCtrl.text = m.config.defaultGeo ?? '';
    _dimensionFilters = Map<String, String>.from(m.config.dimensionFilters);
    _isActive = m.isActive;
    _ifMatchVersion = m.version;
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    final productId = int.tryParse(_productIdCtrl.text.trim());
    if (productId == null) {
      setState(() => _formError = 'product_id must be an integer');
      return;
    }
    setState(() {
      _saving = true;
      _formError = null;
      _dimensionErrors = const {};
    });
    final repo = ref.read(semanticMappingsRepositoryProvider);
    try {
      final (mapping, wasCreated) = await repo.upsert(
        cubeId: _cubeIdCtrl.text.trim(),
        productId: productId,
        semanticKey: _semanticKeyCtrl.text.trim(),
        label: _labelCtrl.text.trim(),
        description: _descriptionCtrl.text.trim().isEmpty
            ? null
            : _descriptionCtrl.text.trim(),
        config: {
          'dimension_filters': _dimensionFilters,
          'measure': _measureCtrl.text.trim(),
          'unit': _unitCtrl.text.trim(),
          'frequency': _frequencyCtrl.text.trim(),
          'supported_metrics': const [
            'current_value',
            'year_over_year_change',
            'previous_period_change',
          ],
          if (_defaultGeoCtrl.text.trim().isNotEmpty)
            'default_geo': _defaultGeoCtrl.text.trim(),
        },
        isActive: _isActive,
        ifMatchVersion: _ifMatchVersion,
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            wasCreated
                ? 'Mapping created (v${mapping.version}).'
                : 'Mapping updated (v${mapping.version}).',
          ),
        ),
      );
      context.go('/semantic-mappings');
    } on DioException catch (error) {
      final payload = BackendErrorPayload.fromDioException(error);
      final code = payload.errorCode;
      if (code == 'VERSION_CONFLICT' && mounted) {
        await VersionConflictModal.show(
          context,
          onReload: () {
            if (widget.mappingId != null) {
              ref.invalidate(semanticMappingProvider(widget.mappingId!));
            }
            setState(() => _hydrated = false);
          },
        );
      } else {
        final fieldErrors = <String, String>{};
        for (final e in payload.fieldErrors ?? const []) {
          final dim = e['dimension_name'];
          final msg = e['message'];
          if (dim is String && msg is String) {
            fieldErrors[dim] = msg;
          }
        }
        setState(() {
          _formError = payload.message ?? 'Save failed.';
          _dimensionErrors = fieldErrors;
        });
      }
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isEdit) {
      final asyncMapping =
          ref.watch(semanticMappingProvider(widget.mappingId!));
      return asyncMapping.when(
        data: (m) {
          _hydrateFrom(m);
          return _buildForm();
        },
        loading: () => const Scaffold(
          body: Center(child: CircularProgressIndicator()),
        ),
        error: (e, _) => Scaffold(
          appBar: AppBar(title: const Text('Edit mapping')),
          body: Center(child: Text('Error: $e')),
        ),
      );
    }
    return _buildForm();
  }

  Widget _buildForm() {
    final cubeIdValue = _cubeIdCtrl.text.trim();
    final cubeMetadataAsync = cubeIdValue.isEmpty
        ? const AsyncValue<CubeMetadataSnapshot?>.data(null)
        : ref.watch(cubeMetadataProvider(cubeIdValue));

    return Scaffold(
      appBar: AppBar(
        title: Text(_isEdit ? 'Edit mapping' : 'New mapping'),
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Form(
            key: _formKey,
            child: ListView(
              children: [
                if (_formError != null)
                  Card(
                    color: Theme.of(context).colorScheme.errorContainer,
                    child: Padding(
                      padding: const EdgeInsets.all(12),
                      child: Text(_formError!),
                    ),
                  ),
                _RequiredText(
                  controller: _cubeIdCtrl,
                  label: 'cube_id',
                  k: const ValueKey('field-cube-id'),
                  onChanged: (_) => setState(() {}),
                ),
                cubeMetadataAsync.when(
                  data: (snap) => snap == null
                      ? const Padding(
                          padding: EdgeInsets.symmetric(vertical: 4),
                          child: Text(
                            'Cube metadata not yet cached — validation will run on submit.',
                            style: TextStyle(fontSize: 12),
                          ),
                        )
                      : const SizedBox.shrink(),
                  loading: () => const SizedBox.shrink(),
                  error: (_, __) => const SizedBox.shrink(),
                ),
                _RequiredText(
                  controller: _productIdCtrl,
                  label: 'product_id',
                  keyboardType: TextInputType.number,
                  k: const ValueKey('field-product-id'),
                ),
                _RequiredText(
                  controller: _semanticKeyCtrl,
                  label: 'semantic_key',
                  k: const ValueKey('field-semantic-key'),
                ),
                _RequiredText(
                  controller: _labelCtrl,
                  label: 'label',
                  k: const ValueKey('field-label'),
                ),
                TextFormField(
                  key: const ValueKey('field-description'),
                  controller: _descriptionCtrl,
                  decoration: const InputDecoration(labelText: 'description'),
                ),
                const SizedBox(height: 12),
                Text(
                  'dimension_filters',
                  style: Theme.of(context).textTheme.titleSmall,
                ),
                DimensionFiltersEditor(
                  value: _dimensionFilters,
                  dimensionErrors: _dimensionErrors,
                  onChanged: (next) =>
                      setState(() => _dimensionFilters = next),
                ),
                _RequiredText(
                  controller: _measureCtrl,
                  label: 'measure',
                  k: const ValueKey('field-measure'),
                ),
                _RequiredText(
                  controller: _unitCtrl,
                  label: 'unit',
                  k: const ValueKey('field-unit'),
                ),
                _RequiredText(
                  controller: _frequencyCtrl,
                  label: 'frequency',
                  k: const ValueKey('field-frequency'),
                ),
                TextFormField(
                  key: const ValueKey('field-default-geo'),
                  controller: _defaultGeoCtrl,
                  decoration: const InputDecoration(labelText: 'default_geo'),
                ),
                CheckboxListTile(
                  key: const ValueKey('field-is-active'),
                  title: const Text('Active'),
                  value: _isActive,
                  onChanged: (v) => setState(() => _isActive = v ?? true),
                ),
                const SizedBox(height: 16),
                FilledButton(
                  key: const ValueKey('form-submit'),
                  onPressed: _saving ? null : _submit,
                  child: Text(_saving ? 'Saving…' : 'Save'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _RequiredText extends StatelessWidget {
  const _RequiredText({
    required this.controller,
    required this.label,
    this.keyboardType,
    this.k,
    this.onChanged,
  });

  final TextEditingController controller;
  final String label;
  final TextInputType? keyboardType;
  final Key? k;
  final ValueChanged<String>? onChanged;

  @override
  Widget build(BuildContext context) {
    return TextFormField(
      key: k,
      controller: controller,
      keyboardType: keyboardType,
      decoration: InputDecoration(labelText: label),
      validator: (v) =>
          (v == null || v.trim().isEmpty) ? '$label is required' : null,
      onChanged: onChanged,
    );
  }
}
