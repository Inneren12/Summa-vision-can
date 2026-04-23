import 'package:flutter/material.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:summa_vision_admin/core/app_bootstrap/app_bootstrap_provider.dart';
import 'package:summa_vision_admin/l10n/generated/app_localizations.dart';

import 'core/routing/app_router.dart';
import 'core/theme/app_theme.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await dotenv.load(fileName: '.env', isOptional: true);
  runApp(const ProviderScope(child: SummaVisionApp()));
}

class SummaVisionApp extends ConsumerWidget {
  const SummaVisionApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final bootstrap = ref.watch(appBootstrapProvider);
    final router = ref.watch(routerProvider);
    // Gate the real MaterialApp.router on resolved bootstrap state to avoid
    // first-frame locale flicker when persisted locale differs from the EN fallback.
    // Splash duration is typically <50ms (one SharedPreferences read).
    return bootstrap.when(
      loading: _BootstrapSplash.new,
      error: (err, st) => _BootstrapError(error: err),
      data: (state) => MaterialApp.router(
        onGenerateTitle: (context) => AppLocalizations.of(context)!.appTitle,
        theme: buildSummaTheme(),
        locale: state.locale,
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        debugShowCheckedModeBanner: false,
        routerConfig: router,
      ),
    );
  }
}

/// Minimal splash while AppBootstrapNotifier resolves locale from SharedPreferences.
/// Duration is typically <50ms — no branding needed, just a neutral placeholder.
class _BootstrapSplash extends StatelessWidget {
  const _BootstrapSplash();

  @override
  Widget build(BuildContext context) {
    return const MaterialApp(
      home: Scaffold(body: Center(child: CircularProgressIndicator())),
    );
  }
}

/// Shown if bootstrap fails (e.g., SharedPreferences plugin error).
/// Rare in practice. Surface the error so it's not silent.
class _BootstrapError extends StatelessWidget {
  const _BootstrapError({required this.error});

  final Object error;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      home: Scaffold(
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Text(
              // i18n-kept: category B (dev/diagnostic). AppLocalizations is
              // not available in this bootstrap-error subtree because it is
              // rendered via a fallback MaterialApp outside MaterialApp.router.
              // See docs/phase-3-slice-3-recon.md Section 6. Debt tracked in
              // DEBT-029 for locale-aware pre-localization fallback.
              'App bootstrap failed: $error',
              textAlign: TextAlign.center,
            ),
          ),
        ),
      ),
    );
  }
}
