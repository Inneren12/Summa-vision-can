import 'package:flutter/material.dart';

/// Reload-prompt dialog shown after a 412 ``VERSION_CONFLICT`` response.
///
/// The action button calls [onReload]; the dismiss button closes without
/// reloading so the operator can choose to abandon their edits.
class VersionConflictModal extends StatelessWidget {
  const VersionConflictModal({
    super.key,
    required this.onReload,
    this.title = 'Version conflict',
    this.body =
        'This mapping was modified by another user. Reload to see the latest version.',
  });

  final VoidCallback onReload;
  final String title;
  final String body;

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      key: const ValueKey('version-conflict-modal'),
      title: Text(title),
      content: Text(body),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(false),
          child: const Text('Dismiss'),
        ),
        FilledButton(
          key: const ValueKey('version-conflict-reload'),
          onPressed: () {
            Navigator.of(context).pop(true);
            onReload();
          },
          child: const Text('Reload'),
        ),
      ],
    );
  }

  static Future<bool?> show(
    BuildContext context, {
    required VoidCallback onReload,
  }) {
    return showDialog<bool>(
      context: context,
      barrierDismissible: false,
      builder: (_) => VersionConflictModal(onReload: onReload),
    );
  }
}
