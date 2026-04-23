import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:summa_vision_admin/core/theme/app_theme.dart';
import 'package:summa_vision_admin/features/queue/data/queue_repository.dart';
import 'package:summa_vision_admin/features/queue/domain/content_brief.dart';
import 'package:summa_vision_admin/features/queue/presentation/queue_screen.dart';
import 'package:summa_vision_admin/l10n/generated/app_localizations.dart';

const _brief = ContentBrief(
  id: 1,
  headline: 'RU smoke headline',
  chartType: 'LINE',
  viralityScore: 7.9,
  status: 'DRAFT',
  createdAt: '2026-03-17T10:00:00Z',
);

Widget _harness(List<ContentBrief> briefs) {
  return ProviderScope(
    overrides: [
      queueProvider.overrideWith((ref) async => briefs),
    ],
    child: MaterialApp(
      theme: AppTheme.dark,
      locale: const Locale('ru'),
      supportedLocales: AppLocalizations.supportedLocales,
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      home: const QueueScreen(),
    ),
  );
}

void main() {
  testWidgets('RU queue screen denies EN literals while allowing chart type', (
    tester,
  ) async {
    await tester.pumpWidget(_harness(const [_brief]));
    await tester.pumpAndSettle();

    expect(find.text('Brief Queue', skipOffstage: false), findsNothing);
    expect(find.text('Refresh queue', skipOffstage: false), findsNothing);
    expect(find.text('Reject', skipOffstage: false), findsNothing);
    expect(find.text('Approve', skipOffstage: false), findsNothing);
    expect(find.textContaining('No briefs in queue', skipOffstage: false), findsNothing);

    // Allowlist check: chart type values may remain EN (Category D).
    expect(find.textContaining('LINE'), findsAtLeastNWidgets(1));
  });

  testWidgets('RU empty state denies EN empty prefix', (tester) async {
    await tester.pumpWidget(_harness(const []));
    await tester.pumpAndSettle();

    expect(find.textContaining('No briefs in queue', skipOffstage: false), findsNothing);
  });
}
