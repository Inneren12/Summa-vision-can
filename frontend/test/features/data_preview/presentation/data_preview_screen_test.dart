import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:summa_vision_admin/core/theme/app_theme.dart';
import 'package:summa_vision_admin/features/cubes/application/cube_providers.dart';
import 'package:summa_vision_admin/features/cubes/data/cube_repository.dart';
import 'package:summa_vision_admin/features/cubes/domain/cube_catalog_entry.dart';
import 'package:summa_vision_admin/features/cubes/presentation/cube_detail_screen.dart';
import 'package:summa_vision_admin/features/data_preview/application/data_preview_providers.dart';
import 'package:summa_vision_admin/features/data_preview/data/data_preview_repository.dart';
import 'package:summa_vision_admin/features/data_preview/domain/data_preview_response.dart';
import 'package:summa_vision_admin/features/data_preview/presentation/data_preview_screen.dart';

// ---------------------------------------------------------------------------
// Sample data — matches real backend contract
// ---------------------------------------------------------------------------

const _sampleColumnNames = ['REF_DATE', 'GEO', 'VALUE', 'STATUS'];

const _sampleData = <Map<String, dynamic>>[
  {'REF_DATE': '2024-01', 'GEO': 'Canada', 'VALUE': 156.2, 'STATUS': 'A'},
  {'REF_DATE': '2024-01', 'GEO': 'Ontario', 'VALUE': 162.1, 'STATUS': 'A'},
  {'REF_DATE': '2024-02', 'GEO': 'Canada', 'VALUE': 157.8, 'STATUS': 'A'},
  {'REF_DATE': '2024-02', 'GEO': 'Ontario', 'VALUE': null, 'STATUS': 'F'},
  {'REF_DATE': '2024-03', 'GEO': 'Canada', 'VALUE': 159.1, 'STATUS': 'A'},
];

const _samplePreview = DataPreviewResponse(
  storageKey: 'statcan/processed/13-10-0888-01/2024-12-15.parquet',
  rows: 48520,
  columns: 4,
  columnNames: _sampleColumnNames,
  data: _sampleData,
);

const _smallPreview = DataPreviewResponse(
  storageKey: 'statcan/processed/13-10-0888-01/2024-12-15.parquet',
  rows: 48520,
  columns: 5,
  columnNames: ['REF_DATE', 'GEO', 'VALUE', 'SCALAR_ID', 'STATUS'],
  data: [
    {'REF_DATE': '2024-01', 'GEO': 'Canada', 'VALUE': 156.2, 'SCALAR_ID': 0, 'STATUS': 'A'},
    {'REF_DATE': '2024-01', 'GEO': 'Ontario', 'VALUE': 162.1, 'SCALAR_ID': 0, 'STATUS': 'A'},
    {'REF_DATE': '2024-02', 'GEO': 'Canada', 'VALUE': 157.8, 'SCALAR_ID': 0, 'STATUS': 'A'},
    {'REF_DATE': '2024-02', 'GEO': 'Ontario', 'VALUE': null, 'SCALAR_ID': 0, 'STATUS': 'F'},
    {'REF_DATE': '2024-03', 'GEO': 'Canada', 'VALUE': 159.1, 'SCALAR_ID': 0, 'STATUS': 'A'},
  ],
);

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/// Wraps the preview screen in a MediaQuery with sufficient width
/// to prevent DropdownButtonFormField overflow in test environment.
Widget _buildPreviewScreen({
  required Override previewOverride,
  String storageKey = 'statcan/processed/13-10-0888-01/2024-12-15.parquet',
  List<Override> extraOverrides = const [],
}) {
  return ProviderScope(
    overrides: [
      previewOverride,
      previewStorageKeyProvider.overrideWith((ref) => storageKey),
      cubeDiffProvider.overrideWith((ref) async => const CubeDiff.noBaseline()),
      ...extraOverrides,
    ],
    child: MaterialApp(
      theme: AppTheme.dark,
      home: MediaQuery(
        data: const MediaQueryData(size: Size(1200, 800)),
        child: DataPreviewScreen(storageKey: storageKey),
      ),
    ),
  );
}

class _FakeDataPreviewRepository extends DataPreviewRepository {
  _FakeDataPreviewRepository() : super(Dio());

  int triggerFetchCallCount = 0;

  @override
  Future<DataPreviewResponse> getPreview(String storageKey,
      {int limit = 100}) async {
    return _samplePreview;
  }

  @override
  Future<String> triggerFetch(String productId) async {
    triggerFetchCallCount++;
    return 'test-fetch-job-id';
  }

  @override
  Future<Map<String, dynamic>> getJobStatus(String jobId) async {
    return {
      'job_id': jobId,
      'status': 'success',
      'result_json':
          '{"storage_key": "statcan/processed/13-10-0888-01/2024-12-15.parquet"}',
    };
  }
}

class _FakeCubeRepository extends CubeRepository {
  _FakeCubeRepository() : super(Dio());

  @override
  Future<CubeCatalogEntry> getByProductId(String productId) async {
    return const CubeCatalogEntry(
      productId: '13-10-0888-01',
      titleEn: 'New housing price index, monthly',
      subjectCode: '18',
      subjectEn: 'Prices and price indexes',
      frequency: 'Monthly',
    );
  }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

void main() {
  group('DataPreviewScreen — loading state', () {
    testWidgets('shows CircularProgressIndicator while loading',
        (tester) async {
      final completer = Completer<DataPreviewResponse?>();

      await tester.pumpWidget(
        _buildPreviewScreen(
          previewOverride: dataPreviewProvider.overrideWith(
            (ref) => completer.future,
          ),
        ),
      );
      await tester.pump();

      expect(find.byType(CircularProgressIndicator), findsOneWidget);
    });
  });

  group('DataPreviewScreen — renders table', () {
    testWidgets('shows DataTable with correct rows and columns',
        (tester) async {
      await tester.pumpWidget(
        _buildPreviewScreen(
          previewOverride: dataPreviewProvider.overrideWith(
            (ref) async => _samplePreview,
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.byType(DataTable), findsOneWidget);
      // 4 column headers
      expect(find.text('REF_DATE'), findsOneWidget);
      expect(find.text('GEO'), findsOneWidget);
      expect(find.text('VALUE'), findsOneWidget);
      expect(find.text('STATUS'), findsOneWidget);
      // 5 data rows — check some cell values
      expect(find.text('Canada'), findsNWidgets(3)); // 3 Canada rows
      expect(find.text('Ontario'), findsNWidgets(2)); // 2 Ontario rows
    });
  });

  group('DataPreviewScreen — row count display', () {
    testWidgets('shows "Showing 5 of 48,520 rows"', (tester) async {
      await tester.pumpWidget(
        _buildPreviewScreen(
          previewOverride: dataPreviewProvider.overrideWith(
            (ref) async => _samplePreview,
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(
        find.textContaining('Showing 5 of 48,520 rows'),
        findsOneWidget,
      );
    });

    testWidgets('shows preview limit note when total > returned',
        (tester) async {
      await tester.pumpWidget(
        _buildPreviewScreen(
          previewOverride: dataPreviewProvider.overrideWith(
            (ref) async => _samplePreview,
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(
        find.text('Preview limited to first 100 rows'),
        findsOneWidget,
      );
    });
  });

  group('DataPreviewScreen — null cell rendering', () {
    testWidgets('renders em dash for null VALUE', (tester) async {
      await tester.pumpWidget(
        _buildPreviewScreen(
          previewOverride: dataPreviewProvider.overrideWith(
            (ref) async => _samplePreview,
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Row index 3 has VALUE=null, should render "—"
      expect(find.text('\u2014'), findsWidgets);
    });
  });

  group('DataPreviewScreen — schema chips', () {
    testWidgets('renders column schema chips when expanded', (tester) async {
      await tester.pumpWidget(
        _buildPreviewScreen(
          previewOverride: dataPreviewProvider.overrideWith(
            (ref) async => _smallPreview,
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Expand the schema inspector
      await tester.tap(find.textContaining('Column Schema'));
      await tester.pumpAndSettle();

      // Schema chips show inferred dtypes from first data row
      expect(find.text('REF_DATE (str)'), findsOneWidget);
      expect(find.text('GEO (str)'), findsOneWidget);
      expect(find.text('VALUE (float64)'), findsOneWidget);
      expect(find.text('SCALAR_ID (int64)'), findsOneWidget);
      expect(find.text('STATUS (str)'), findsOneWidget);
    });
  });

  group('DataPreviewScreen — GEO filter', () {
    testWidgets('filtering by geography shows only matching rows',
        (tester) async {
      await tester.pumpWidget(
        _buildPreviewScreen(
          previewOverride: dataPreviewProvider.overrideWith(
            (ref) async => _samplePreview,
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Open the GEO dropdown
      await tester.tap(find.text('All geographies'));
      await tester.pumpAndSettle();

      // Select "Ontario"
      await tester.tap(find.text('Ontario').last);
      await tester.pumpAndSettle();

      // Should only show Ontario rows (2 of them)
      final dataTable = tester.widget<DataTable>(find.byType(DataTable));
      expect(dataTable.rows.length, 2);
    });
  });

  group('DataPreviewScreen — clear filters', () {
    testWidgets('Clear Filters resets all filters', (tester) async {
      await tester.pumpWidget(
        _buildPreviewScreen(
          previewOverride: dataPreviewProvider.overrideWith(
            (ref) async => _samplePreview,
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Apply a geo filter first
      await tester.tap(find.text('All geographies'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Ontario').last);
      await tester.pumpAndSettle();

      // Verify filtered
      var dataTable = tester.widget<DataTable>(find.byType(DataTable));
      expect(dataTable.rows.length, 2);

      // Clear filters
      await tester.tap(find.text('Clear Filters'));
      await tester.pumpAndSettle();

      // All rows visible again
      dataTable = tester.widget<DataTable>(find.byType(DataTable));
      expect(dataTable.rows.length, 5);
    });
  });

  group('DataPreviewScreen — column sort', () {
    testWidgets('tapping column header sorts rows', (tester) async {
      await tester.pumpWidget(
        _buildPreviewScreen(
          previewOverride: dataPreviewProvider.overrideWith(
            (ref) async => _samplePreview,
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Tap the GEO column header to sort
      await tester.tap(find.text('GEO'));
      await tester.pumpAndSettle();

      final dataTable = tester.widget<DataTable>(find.byType(DataTable));
      expect(dataTable.sortColumnIndex, isNotNull);
    });
  });

  group('DataPreviewScreen — error state', () {
    testWidgets('shows error message and retry button', (tester) async {
      await tester.pumpWidget(
        _buildPreviewScreen(
          previewOverride: dataPreviewProvider.overrideWith(
            (ref) => Future<DataPreviewResponse?>.error('Network error'),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.textContaining('Failed to load preview'), findsOneWidget);
      expect(find.text('Retry'), findsOneWidget);
    });
  });

  group('CubeDetailScreen — Fetch Data', () {
    testWidgets('tapping Fetch Data triggers triggerFetch', (tester) async {
      final fakePreviewRepo = _FakeDataPreviewRepository();
      final fakeCubeRepo = _FakeCubeRepository();

      final router = GoRouter(
        initialLocation: '/cubes/13-10-0888-01',
        routes: [
          GoRoute(
            path: '/cubes/:productId',
            builder: (_, state) {
              final productId = state.pathParameters['productId'] ?? '';
              return CubeDetailScreen(productId: productId);
            },
          ),
          GoRoute(
            path: '/data/preview',
            builder: (_, state) =>
                const Scaffold(body: Text('Preview Screen')),
          ),
        ],
      );

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            dataPreviewRepositoryProvider
                .overrideWithValue(fakePreviewRepo),
            cubeRepositoryProvider.overrideWithValue(fakeCubeRepo),
            cubeDetailProvider('13-10-0888-01').overrideWith(
              (ref) async => const CubeCatalogEntry(
                productId: '13-10-0888-01',
                titleEn: 'New housing price index, monthly',
                subjectCode: '18',
                subjectEn: 'Prices and price indexes',
                frequency: 'Monthly',
              ),
            ),
          ],
          child: MaterialApp.router(
            theme: AppTheme.dark,
            routerConfig: router,
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Tap Fetch Data
      await tester.tap(find.text('Fetch Data'));
      await tester.pumpAndSettle();

      expect(fakePreviewRepo.triggerFetchCallCount, 1);
    });
  });
}
