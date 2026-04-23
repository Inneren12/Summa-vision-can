import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:summa_vision_admin/core/app_bootstrap/app_bootstrap_provider.dart';
import 'package:summa_vision_admin/l10n/generated/app_localizations.dart';

/// Compact language switcher for the app shell.
///
/// Renders two pill buttons (EN / RU). Tapping a button changes the active
/// locale via AppBootstrapNotifier, which persists to SharedPreferences.
class LanguageSwitcher extends ConsumerWidget {
  const LanguageSwitcher({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final loc = AppLocalizations.of(context)!;
    final currentLocale =
        ref.watch(appBootstrapProvider).valueOrNull?.locale ??
        const Locale('en');
    final currentCode = currentLocale.languageCode;

    return Wrap(
      crossAxisAlignment: WrapCrossAlignment.center,
      spacing: 4,
      runSpacing: 4,
      children: [
        Padding(
          padding: const EdgeInsets.only(right: 4),
          child: Text(
            loc.languageLabel,
            style: Theme.of(context).textTheme.labelSmall,
          ),
        ),
        _LanguageButton(
          label: loc.languageEnglish,
          code: 'en',
          active: currentCode == 'en',
        ),
        _LanguageButton(
          label: loc.languageRussian,
          code: 'ru',
          active: currentCode == 'ru',
        ),
      ],
    );
  }
}

class _LanguageButton extends ConsumerWidget {
  final String label;
  final String code;
  final bool active;

  const _LanguageButton({
    required this.label,
    required this.code,
    required this.active,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    return TextButton(
      onPressed: active
          ? null
          : () => ref.read(appBootstrapProvider.notifier).setLocale(
                Locale(code),
              ),
      style: TextButton.styleFrom(
        minimumSize: const Size(40, 32),
        padding: const EdgeInsets.symmetric(horizontal: 10),
        backgroundColor:
            active ? theme.colorScheme.secondaryContainer : Colors.transparent,
        foregroundColor: active
            ? theme.colorScheme.onSecondaryContainer
            : theme.colorScheme.onSurfaceVariant,
      ),
      child: Text(label),
    );
  }
}
