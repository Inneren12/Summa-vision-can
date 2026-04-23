import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:summa_vision_admin/core/theme/app_theme.dart';
import 'package:summa_vision_admin/features/queue/data/queue_repository.dart';
import 'package:summa_vision_admin/features/queue/domain/content_brief.dart';
import 'package:summa_vision_admin/features/queue/presentation/queue_screen.dart';
import 'package:summa_vision_admin/l10n/generated/app_localizations.dart';

Widget _buildHarness({
  required Locale locale,
  required List<ContentBrief> briefs,
}) {
  return ProviderScope(
    overrides: [
      queueProvider.overrideWith((ref) async => briefs),
    ],
    child: MaterialApp(
      theme: AppTheme.dark,
      locale: locale,
      supportedLocales: AppLocalizations.supportedLocales,
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      home: const QueueScreen(),
    ),
  );
}

AppLocalizations _l10n(WidgetTester tester) {
  final context = tester.element(find.byType(QueueScreen));
  return AppLocalizations.of(context)!;
}

const _sampleBrief = ContentBrief(
  id: 1,
  headline: 'Sample headline',
  chartType: 'LINE',
  viralityScore: 8.4,
  status: 'DRAFT',
  createdAt: '2026-03-17T10:00:00Z',
);

void main() {
  group('QueueScreen localization', () {
    testWidgets('renders localized title and empty state in EN', (tester) async {
      await tester.pumpWidget(
        _buildHarness(
          locale: const Locale('en'),
          briefs: const [],
        ),
      );
      await tester.pumpAndSettle();

      final appLoc = _l10n(tester);
      expect(find.text(appLoc.queueTitle), findsOneWidget);
      expect(find.text(appLoc.queueEmptyState), findsOneWidget);
    });

    testWidgets('renders localized title and empty state in RU', (tester) async {
      await tester.pumpWidget(
        _buildHarness(
          locale: const Locale('ru'),
          briefs: const [],
        ),
      );
      await tester.pumpAndSettle();

      final appLoc = _l10n(tester);
      expect(find.text(appLoc.queueTitle), findsOneWidget);
      expect(find.text(appLoc.queueEmptyState), findsOneWidget);
    });

    testWidgets('renders localized action buttons for populated queue', (
      tester,
    ) async {
      await tester.pumpWidget(
        _buildHarness(
          locale: const Locale('ru'),
          briefs: const [_sampleBrief],
        ),
      );
      await tester.pumpAndSettle();

      final appLoc = _l10n(tester);
      expect(find.text(appLoc.queueRejectVerb), findsOneWidget);
      expect(find.text(appLoc.queueApproveVerb), findsOneWidget);
    });
  });
}
