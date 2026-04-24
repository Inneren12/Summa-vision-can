import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:summa_vision_admin/features/graphics/domain/generation_notifier.dart';
import 'package:summa_vision_admin/features/graphics/domain/generation_state.dart';
import 'package:summa_vision_admin/features/graphics/presentation/preview_screen.dart';
import 'package:summa_vision_admin/l10n/generated/app_localizations.dart';

import '../../../helpers/localized_pump.dart';

/// Mock notifier that fixes initial state without triggering generation.
class _MockGenerationNotifier extends GenerationNotifier {
  _MockGenerationNotifier(this._fixed);
  final GenerationState _fixed;

  @override
  GenerationState build() => _fixed;

  @override
  Future<void> generate(int briefId) async {
    // no-op in tests
  }
}

Future<void> _pump(
  WidgetTester tester,
  GenerationState initial, {
  Locale locale = const Locale('en'),
}) {
  return pumpLocalizedWidget(
    tester,
    const PreviewScreen(taskId: '1'),
    locale: locale,
    overrides: [
      generationNotifierProvider.overrideWith(
        () => _MockGenerationNotifier(initial),
      ),
    ],
  );
}

AppLocalizations _l10n(WidgetTester tester) {
  final ctx = tester.element(find.byType(PreviewScreen));
  return AppLocalizations.of(ctx)!;
}

void main() {
  group('PreviewScreen localization — EN', () {
    testWidgets('submitting phase renders localized status + appbar', (tester) async {
      await _pump(tester, const GenerationState(phase: GenerationPhase.submitting));
      await tester.pump();

      final l10n = _l10n(tester);
      expect(find.text(l10n.previewAppBarTitle), findsOneWidget);
      expect(find.text(l10n.generationStatusSubmitting), findsOneWidget);
    });

    testWidgets('polling phase renders counter + eta', (tester) async {
      await _pump(
        tester,
        const GenerationState(phase: GenerationPhase.polling, pollAttempts: 3),
      );
      await tester.pump();

      final l10n = _l10n(tester);
      expect(
        find.text(l10n.generationStatusPolling(3, GenerationState.maxPollAttempts)),
        findsOneWidget,
      );
      expect(find.text(l10n.previewEtaText), findsOneWidget);
    });

    testWidgets('completed phase renders download button', (tester) async {
      await _pump(
        tester,
        const GenerationState(
          phase: GenerationPhase.completed,
          resultUrl: 'https://placehold.co/1200x628.png',
        ),
      );
      await tester.pump();

      final l10n = _l10n(tester);
      expect(find.text(l10n.previewDownloadButton), findsOneWidget);
    });

    testWidgets('failed phase renders generic localized fallback', (tester) async {
      await _pump(
        tester,
        const GenerationState(phase: GenerationPhase.failed),
      );
      await tester.pump();

      final l10n = _l10n(tester);
      expect(find.text(l10n.generationStatusFailed), findsOneWidget);
      expect(find.text(l10n.commonRetryVerb), findsOneWidget);
    });

    testWidgets('timeout phase renders unified timeout status + retry', (tester) async {
      await _pump(
        tester,
        const GenerationState(phase: GenerationPhase.timeout),
      );
      await tester.pump();

      final l10n = _l10n(tester);
      expect(find.text(l10n.generationStatusTimeout), findsOneWidget);
      expect(find.text(l10n.commonRetryVerb), findsOneWidget);
    });
  });

  group('PreviewScreen localization — RU', () {
    testWidgets('submitting phase renders localized RU status', (tester) async {
      await _pump(
        tester,
        const GenerationState(phase: GenerationPhase.submitting),
        locale: const Locale('ru'),
      );
      await tester.pump();

      final l10n = _l10n(tester);
      expect(find.text(l10n.previewAppBarTitle), findsOneWidget);
      expect(find.text(l10n.generationStatusSubmitting), findsOneWidget);
    });

    testWidgets('polling + eta localized in RU', (tester) async {
      await _pump(
        tester,
        const GenerationState(phase: GenerationPhase.polling, pollAttempts: 5),
        locale: const Locale('ru'),
      );
      await tester.pump();

      final l10n = _l10n(tester);
      expect(
        find.text(l10n.generationStatusPolling(5, GenerationState.maxPollAttempts)),
        findsOneWidget,
      );
      expect(find.text(l10n.previewEtaText), findsOneWidget);
    });

    testWidgets('timeout renders localized RU status', (tester) async {
      await _pump(
        tester,
        const GenerationState(phase: GenerationPhase.timeout),
        locale: const Locale('ru'),
      );
      await tester.pump();

      final l10n = _l10n(tester);
      expect(find.text(l10n.generationStatusTimeout), findsOneWidget);
    });
  });
}
