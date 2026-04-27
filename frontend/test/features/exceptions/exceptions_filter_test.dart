import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:summa_vision_admin/features/exceptions/application/exceptions_providers.dart';
import 'package:summa_vision_admin/features/exceptions/domain/exception_filter.dart';
import 'package:summa_vision_admin/features/exceptions/presentation/exceptions_screen.dart';
import 'package:summa_vision_admin/features/jobs/data/job_dashboard_repository.dart';
import 'package:summa_vision_admin/features/jobs/domain/job_list_response.dart';
import 'package:summa_vision_admin/l10n/generated/app_localizations.dart';

import '../../helpers/localized_pump.dart';

class _EmptyRepository extends JobDashboardRepository {
  _EmptyRepository() : super(Dio());

  @override
  Future<JobListResponse> listJobs({
    String? jobType,
    String? status,
    int limit = 50,
  }) async {
    return JobListResponse(items: [], total: 0);
  }
}

AppLocalizations _l10n(WidgetTester tester) {
  final scaffold = find.byType(Scaffold, skipOffstage: false);
  expect(scaffold, findsAtLeastNWidgets(1));
  return AppLocalizations.of(tester.element(scaffold.first))!;
}

ChoiceChip _findChipWithText(WidgetTester tester, String label) {
  final finder = find.widgetWithText(
    ChoiceChip,
    label,
    skipOffstage: false,
  );
  expect(finder, findsOneWidget,
      reason: 'Expected exactly one ChoiceChip with label "$label"');
  return tester.widget<ChoiceChip>(finder);
}

void main() {
  group('ExceptionFilter enum', () {
    test('has exactly three values: all, failedExports, zombieJobs', () {
      expect(ExceptionFilter.values, hasLength(3));
      expect(
        ExceptionFilter.values.toSet(),
        equals({
          ExceptionFilter.all,
          ExceptionFilter.failedExports,
          ExceptionFilter.zombieJobs,
        }),
      );
    });
  });

  group('Filter chip rendering — selected/unselected state', () {
    Future<void> pumpWithFilter(
      WidgetTester tester,
      ExceptionFilter? initial,
    ) async {
      await pumpLocalizedWidget(
        tester,
        const ExceptionsScreen(),
        overrides: [
          jobDashboardRepositoryProvider
              .overrideWith((ref) => _EmptyRepository()),
          if (initial != null)
            exceptionsFilterProvider.overrideWith((ref) => initial),
        ],
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 50));
    }

    testWidgets('default state: All chip is selected, others are not',
        (tester) async {
      await pumpWithFilter(tester, null);
      final l10n = _l10n(tester);

      final all = _findChipWithText(tester, l10n.exceptionsFilterAll);
      final fe =
          _findChipWithText(tester, l10n.exceptionsFilterFailedExports);
      final zo =
          _findChipWithText(tester, l10n.exceptionsFilterZombieJobs);

      expect(all.selected, isTrue,
          reason: 'default ExceptionFilter is .all → All chip selected');
      expect(fe.selected, isFalse);
      expect(zo.selected, isFalse);
    });

    testWidgets('failedExports filter: Failed Exports chip is selected',
        (tester) async {
      await pumpWithFilter(tester, ExceptionFilter.failedExports);
      final l10n = _l10n(tester);

      final all = _findChipWithText(tester, l10n.exceptionsFilterAll);
      final fe =
          _findChipWithText(tester, l10n.exceptionsFilterFailedExports);
      final zo =
          _findChipWithText(tester, l10n.exceptionsFilterZombieJobs);

      expect(all.selected, isFalse);
      expect(fe.selected, isTrue);
      expect(zo.selected, isFalse);
    });

    testWidgets('zombieJobs filter: Zombie Jobs chip is selected',
        (tester) async {
      await pumpWithFilter(tester, ExceptionFilter.zombieJobs);
      final l10n = _l10n(tester);

      final all = _findChipWithText(tester, l10n.exceptionsFilterAll);
      final fe =
          _findChipWithText(tester, l10n.exceptionsFilterFailedExports);
      final zo =
          _findChipWithText(tester, l10n.exceptionsFilterZombieJobs);

      expect(all.selected, isFalse);
      expect(fe.selected, isFalse);
      expect(zo.selected, isTrue);
    });
  });
}
