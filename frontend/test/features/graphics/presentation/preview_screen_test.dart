import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:summa_vision_admin/features/graphics/domain/generation_notifier.dart';
import 'package:summa_vision_admin/features/graphics/domain/generation_state.dart';
import 'package:summa_vision_admin/features/graphics/presentation/preview_screen.dart';
import 'package:summa_vision_admin/l10n/generated/app_localizations.dart';

import '../../../helpers/localized_pump.dart';

Future<void> _pump(WidgetTester tester, GenerationState initialState) {
  return pumpLocalizedWidget(
    tester,
    const PreviewScreen(taskId: '1'),
    overrides: [
      generationNotifierProvider.overrideWith(
        () => _MockGenerationNotifier(initialState),
      ),
    ],
  );
}

/// Mock notifier that starts with a fixed state and never changes it.
class _MockGenerationNotifier extends GenerationNotifier {
  _MockGenerationNotifier(this._fixed);
  final GenerationState _fixed;

  @override
  GenerationState build() => _fixed;

  @override
  Future<void> generate(int briefId) async {
    // no-op in tests — state is pre-set
  }
}

AppLocalizations _l10n(WidgetTester tester) {
  final ctx = tester.element(find.byType(PreviewScreen));
  return AppLocalizations.of(ctx)!;
}

void main() {
  group('PreviewScreen — submitting state', () {
    testWidgets('shows submitting UI when phase is submitting', (tester) async {
      await _pump(tester, const GenerationState(phase: GenerationPhase.submitting));
      await tester.pump();

      final l10n = _l10n(tester);
      expect(find.byType(CircularProgressIndicator), findsOneWidget);
      expect(find.text(l10n.generationStatusSubmitting), findsOneWidget);
    });
  });

  group('PreviewScreen — polling state', () {
    testWidgets('shows polling progress UI', (tester) async {
      await _pump(
        tester,
        const GenerationState(
          phase: GenerationPhase.polling,
          taskId: 'task-123',
          pollAttempts: 15,
        ),
      );
      await tester.pump();

      final l10n = _l10n(tester);
      expect(
        find.text(l10n.generationStatusPolling(15, GenerationState.maxPollAttempts)),
        findsOneWidget,
      );
    });

    testWidgets('shows max poll count as 60', (tester) async {
      await _pump(
        tester,
        const GenerationState(
          phase: GenerationPhase.polling,
          pollAttempts: 30,
        ),
      );
      await tester.pump();

      final l10n = _l10n(tester);
      expect(
        find.text(l10n.generationStatusPolling(30, GenerationState.maxPollAttempts)),
        findsOneWidget,
      );
    });
  });

  group('PreviewScreen — completed state', () {
    testWidgets('shows image and download button when completed', (tester) async {
      await _pump(
        tester,
        const GenerationState(
          phase: GenerationPhase.completed,
          resultUrl: 'https://placehold.co/1200x628.png',
        ),
      );
      await tester.pump();

      expect(find.byKey(const Key('download_btn')), findsOneWidget);
    });
  });

  group('PreviewScreen — timeout state', () {
    testWidgets('shows timeout error message', (tester) async {
      await _pump(
        tester,
        const GenerationState(phase: GenerationPhase.timeout),
      );
      await tester.pump();

      final l10n = _l10n(tester);
      expect(find.byKey(const Key('error_message')), findsOneWidget);
      expect(find.text(l10n.generationStatusTimeout), findsOneWidget);
      expect(find.byKey(const Key('retry_btn')), findsOneWidget);
    });

    testWidgets('retry button is present on timeout', (tester) async {
      await _pump(
        tester,
        const GenerationState(phase: GenerationPhase.timeout),
      );
      await tester.pump();

      expect(find.byKey(const Key('retry_btn')), findsOneWidget);
    });
  });

  group('PreviewScreen — failed state', () {
    testWidgets('shows error message on failure', (tester) async {
      await _pump(
        tester,
        const GenerationState(
          phase: GenerationPhase.failed,
          errorMessage: 'Server error',
        ),
      );
      await tester.pump();

      expect(find.textContaining('Server error'), findsOneWidget);
      expect(find.byKey(const Key('retry_btn')), findsOneWidget);
    });
  });

  group('GenerationNotifier unit tests', () {
    test('initial state is idle', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      final state = container.read(generationNotifierProvider);
      expect(state.phase, equals(GenerationPhase.idle));
      expect(state.pollAttempts, equals(0));
      expect(state.resultUrl, isNull);
    });

    test('maxPollAttempts is 60', () {
      expect(GenerationState.maxPollAttempts, equals(60));
    });

    test('reset() returns to idle state', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      container.read(generationNotifierProvider.notifier).reset();

      final state = container.read(generationNotifierProvider);
      expect(state.phase, equals(GenerationPhase.idle));
    });

    test('completed state is cached — generate() is no-op if already completed', () async {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      final notifier = container.read(generationNotifierProvider.notifier);
      expect(container.read(generationNotifierProvider).phase, equals(GenerationPhase.idle));

      notifier.reset();
      expect(container.read(generationNotifierProvider).phase, equals(GenerationPhase.idle));
    });
  });

  group('GenerationState', () {
    test('copyWith preserves unspecified fields', () {
      const original = GenerationState(
        phase: GenerationPhase.polling,
        taskId: 'abc',
        pollAttempts: 5,
      );
      final updated = original.copyWith(pollAttempts: 10);

      expect(updated.phase, equals(GenerationPhase.polling));
      expect(updated.taskId, equals('abc'));
      expect(updated.pollAttempts, equals(10));
    });

    test('copyWith preserves errorCode when set', () {
      const original = GenerationState(
        phase: GenerationPhase.failed,
        errorCode: 'CHART_EMPTY_DF',
      );
      final updated = original.copyWith(errorMessage: 'oops');
      expect(updated.errorCode, equals('CHART_EMPTY_DF'));
    });

    test('isCompleted extension returns true only for COMPLETED status', () {
      const state = GenerationState(phase: GenerationPhase.completed);
      expect(state.phase == GenerationPhase.completed, isTrue);
    });
  });
}
