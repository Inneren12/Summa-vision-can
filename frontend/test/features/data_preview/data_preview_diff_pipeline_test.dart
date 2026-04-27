// ignore_for_file: avoid_print

import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:hive/hive.dart';
import 'package:summa_vision_admin/core/theme/app_theme.dart';
import 'package:summa_vision_admin/features/data_preview/application/cube_diff_service.dart';
import 'package:summa_vision_admin/features/data_preview/application/data_preview_providers.dart';
import 'package:summa_vision_admin/features/data_preview/domain/data_preview_response.dart';
import 'package:summa_vision_admin/features/data_preview/presentation/data_preview_screen.dart';
import 'package:summa_vision_admin/l10n/generated/app_localizations.dart';

void _bc(String tag) {
  // Breadcrumb. Forces flush so CI log preserves order even on hang.
  print('### BREADCRUMB ### $tag @ ${DateTime.now().toIso8601String()}');
}

void main() {
  testWidgets('first view no baseline, refresh shows 1 change and highlight',
      (tester) async {
    _bc('00-test-entry');

    // dart:io and Hive must run in the real-async zone, not testWidgets'
    // fake zone. Without runAsync, Directory.systemTemp.createTemp hangs
    // because the fake zone's microtask handling blocks real I/O futures.
    // Round 4 breadcrumbs proved the hang was on createTemp: only
    // 00-test-entry printed before the 10-min timeout.
    late final Directory tempDir;
    late final Box box;
    await tester.runAsync(() async {
      _bc('00a-runAsync-entered');
      tempDir = await Directory.systemTemp.createTemp('cube_diff_pipeline_');
      _bc('01-tempdir-created');

      await Hive.close();
      _bc('02-hive-defensive-close-done');

      Hive.init(tempDir.path);
      _bc('03-hive-init-done');

      box = await Hive.openBox(
          'cube_diff_pipeline_${DateTime.now().microsecondsSinceEpoch}');
      _bc('04-hive-openbox-done');
    });
    _bc('04a-runAsync-exited');

    addTearDown(() async {
      _bc('99-teardown-start');
      // Teardown also touches dart:io (deleteFromDisk, tempDir.delete) and
      // Hive — same reason, must be runAsync. Use the binding rather than
      // tester.runAsync because tester may be disposed by the time
      // addTearDown fires; the binding outlives the tester.
      // Each step is wrapped with try/catch + 5s timeout so a hang in one
      // step doesn't block the others — test outcome is determined by
      // assertions, not teardown.
      try {
        await TestWidgetsFlutterBinding.instance.runAsync(() async {
          _bc('99-teardown-runAsync-entered');
          try {
            await box.deleteFromDisk().timeout(const Duration(seconds: 5));
            _bc('99-teardown-deletefromdisk-done');
          } catch (e) {
            _bc('99-teardown-deletefromdisk-skipped: $e');
          }
          try {
            await Hive.close().timeout(const Duration(seconds: 5));
            _bc('99-teardown-hive-close-done');
          } catch (e) {
            _bc('99-teardown-hive-close-skipped: $e');
          }
          try {
            await tempDir
                .delete(recursive: true)
                .timeout(const Duration(seconds: 5));
            _bc('99-teardown-tempdir-delete-done');
          } catch (e) {
            _bc('99-teardown-tempdir-delete-skipped: $e');
          }
        });
      } catch (e) {
        _bc('99-teardown-outer-error: $e');
      }
    });

    const storageKey = 'statcan/processed/13-10-0888-01/2024-12-15.parquet';
    const firstResponse = DataPreviewResponse(
      storageKey: storageKey,
      rows: 2,
      columns: 2,
      columnNames: ['A', 'B'],
      data: [
        {'A': 1, 'B': 'x'},
        {'A': 2, 'B': 'y'},
      ],
      productId: '13-10-0888-01',
    );
    const secondResponse = DataPreviewResponse(
      storageKey: storageKey,
      rows: 2,
      columns: 2,
      columnNames: ['A', 'B'],
      data: [
        {'A': 1, 'B': 'x'},
        {'A': 2, 'B': 'z'},
      ],
      productId: '13-10-0888-01',
    );

    var fetchCount = 0;
    DataPreviewResponse currentResponse() {
      _bc('FETCH-$fetchCount-called');
      final r = fetchCount++ == 0 ? firstResponse : secondResponse;
      _bc('FETCH-returning-idx-${fetchCount - 1}');
      return r;
    }

    // Sequence the cubeDiff results in lockstep with the dataPreview fetches.
    // First read (after first dataPreview): NoBaseline (matches "first view" UI).
    // Second read (after invalidate): Computed with one cell change at row 1, col B
    //   (matches the change between firstResponse and secondResponse data).
    // Overriding the provider keeps Hive box.put off the read path, which
    // round 6 proved hangs on reentrant-runAsync inside the testWidgets fake
    // zone. The real cubeDiffService logic is exercised by
    // cube_diff_service_test.dart.
    var diffCount = 0;
    CubeDiff currentDiff() {
      _bc('DIFF-$diffCount-called');
      final CubeDiff d;
      if (diffCount == 0) {
        d = const CubeDiff.noBaseline();
      } else {
        d = CubeDiff.computed(
          changedCells: <DiffCellKey>{const DiffCellKey(1, 'B')},
        );
      }
      diffCount++;
      _bc('DIFF-returning-idx-${diffCount - 1}');
      return d;
    }

    _bc('05-creating-container');
    final container = ProviderContainer(
      overrides: [
        cubeDiffSnapshotsBoxProvider.overrideWithValue(box),
        previewStorageKeyProvider.overrideWith((ref) => storageKey),
        dataPreviewProvider.overrideWith((ref) async {
          _bc('OVERRIDE-dataPreview-body-entered');
          ref.watch(previewStorageKeyProvider);
          final r = currentResponse();
          _bc('OVERRIDE-dataPreview-body-returning');
          return r;
        }),
        cubeDiffProvider.overrideWith((ref) async {
          _bc('OVERRIDE-cubeDiff-body-entered');
          // Watch dataPreview so cubeDiff invalidation tracks dataPreview
          // changes (same dependency the real provider has).
          await ref.watch(dataPreviewProvider.future);
          final d = currentDiff();
          _bc('OVERRIDE-cubeDiff-body-returning');
          return d;
        }),
      ],
    );
    _bc('06-container-created');
    addTearDown(() {
      _bc('99-container-dispose-start');
      container.dispose();
      _bc('99-container-dispose-done');
    });

    _bc('07-pumpWidget-start');
    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: MaterialApp(
          theme: AppTheme.dark,
          localizationsDelegates: AppLocalizations.localizationsDelegates,
          supportedLocales: AppLocalizations.supportedLocales,
          home: MediaQuery(
            data: const MediaQueryData(size: Size(1200, 800)),
            child: DataPreviewScreen(storageKey: storageKey),
          ),
        ),
      ),
    );
    _bc('08-pumpWidget-returned');

    _bc('09-pumpAndSettle-1-start');
    await tester.pumpAndSettle(const Duration(seconds: 2));
    _bc('10-pumpAndSettle-1-returned');

    _bc('11-asserting-first-banner');
    final element1 = tester.element(find.byType(DataPreviewScreen));
    final l10n1 = AppLocalizations.of(element1)!;
    expect(
      find.text(l10n1.dataPreviewDiffNoBaseline, skipOffstage: false),
      findsAtLeastNWidgets(1),
    );
    _bc('12-first-banner-asserted');

    expect(fetchCount, 1, reason: 'First fetch must have run exactly once');
    _bc('13-fetchcount-1-confirmed');

    expect(diffCount, 1, reason: 'First diff fetch must have run exactly once');
    _bc('13a-diffcount-1-confirmed');

    _bc('14-invalidating-dataPreviewProvider');
    container.invalidate(dataPreviewProvider);
    _bc('15-invalidated-dataPreviewProvider');

    _bc('16-invalidating-cubeDiffProvider');
    container.invalidate(cubeDiffProvider);
    _bc('17-invalidated-cubeDiffProvider');

    _bc('18-pumpAndSettle-2-start');
    await tester.pumpAndSettle(const Duration(seconds: 2));
    _bc('19-pumpAndSettle-2-returned');

    expect(fetchCount, 2, reason: 'Second fetch must have run after invalidate');
    _bc('20-fetchcount-2-confirmed');

    expect(diffCount, 2,
        reason: 'Second diff fetch must have run after invalidate');
    _bc('20a-diffcount-2-confirmed');

    _bc('21-asserting-second-banner');
    final element2 = tester.element(find.byType(DataPreviewScreen));
    final l10n2 = AppLocalizations.of(element2)!;
    expect(
      find.text(l10n2.dataPreviewDiffStatusLabel(1), skipOffstage: false),
      findsAtLeastNWidgets(1),
    );
    _bc('22-second-banner-asserted');

    final accent = AppTheme.dark.extension<SummaTheme>()!.accentMuted;
    final highlighted =
        find.byWidgetPredicate((w) => w is Container && w.color == accent);
    _bc('23-asserting-highlight');
    expect(highlighted, findsAtLeastNWidgets(1));
    _bc('24-highlight-asserted');

    _bc('25-test-body-complete');
  });
}
