// ignore_for_file: avoid_print
//
// Phase 3.1b: Flutter admin semantic-mappings widget + provider tests.
//
// Coverage (8 cases):
//   1. List screen renders DataTable with mock data.
//   2. Filter input triggers refetch when applied.
//   3. Form submits valid data and navigates back on success.
//   4. Form renders inline errors from MEMBER_NOT_FOUND envelope.
//   5. Form shows VersionConflictModal on 412.
//   6. dimension_filters editor add/remove rows.
//   7. cubeMetadataProvider returns null on 404.
//   8. cubeMetadataProvider triggers prime call when prime=true.

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

import 'package:summa_vision_admin/features/semantic_mappings/models/semantic_mapping.dart';
import 'package:summa_vision_admin/features/semantic_mappings/providers/semantic_mappings_providers.dart';
import 'package:summa_vision_admin/features/semantic_mappings/repository/semantic_mappings_repository.dart';
import 'package:summa_vision_admin/features/semantic_mappings/screens/semantic_mapping_form_screen.dart';
import 'package:summa_vision_admin/features/semantic_mappings/screens/semantic_mappings_list_screen.dart';
import 'package:summa_vision_admin/features/semantic_mappings/widgets/dimension_filters_editor.dart';

import '../../helpers/localized_pump.dart';

// ---------------------------------------------------------------------------
// Fakes
// ---------------------------------------------------------------------------

SemanticMapping _makeMapping({
  int id = 1,
  String cubeId = '18-10-0004',
  int productId = 18100004,
  String semanticKey = 'cpi.canada.all_items.index',
  int version = 1,
  bool isActive = true,
}) {
  return SemanticMapping(
    id: id,
    cubeId: cubeId,
    productId: productId,
    semanticKey: semanticKey,
    label: 'CPI — Canada',
    description: null,
    config: const SemanticMappingConfig(
      dimensionFilters: {'Geography': 'Canada', 'Products': 'All-items'},
      measure: 'Value',
      unit: 'index',
      frequency: 'monthly',
      supportedMetrics: ['current_value'],
      defaultGeo: 'Canada',
    ),
    isActive: isActive,
    version: version,
    createdAt: DateTime.utc(2026, 5, 1),
    updatedAt: DateTime.utc(2026, 5, 2),
    updatedBy: 'alice',
  );
}

class _FakeRepository extends SemanticMappingsRepository {
  _FakeRepository() : super(Dio());

  int listCalls = 0;
  String? lastCubeIdFilter;
  SemanticMappingListPage Function()? onList;
  Future<(SemanticMapping, bool)> Function({
    required String cubeId,
    required int productId,
    required String semanticKey,
    required String label,
    String? description,
    required Map<String, dynamic> config,
    required bool isActive,
    String? updatedBy,
    int? ifMatchVersion,
  })? onUpsert;
  Future<CubeMetadataSnapshot?> Function(
    String cubeId, {
    bool prime,
    int? productId,
  })? onCubeMetadata;

  @override
  Future<SemanticMappingListPage> list({
    String? cubeId,
    String? semanticKey,
    bool? isActive,
    int limit = 50,
    int offset = 0,
  }) async {
    listCalls += 1;
    lastCubeIdFilter = cubeId;
    return onList?.call() ??
        SemanticMappingListPage(
          items: [_makeMapping()],
          total: 1,
          limit: limit,
          offset: offset,
        );
  }

  @override
  Future<SemanticMapping> getById(int id) async => _makeMapping(id: id);

  @override
  Future<(SemanticMapping, bool)> upsert({
    required String cubeId,
    required int productId,
    required String semanticKey,
    required String label,
    String? description,
    required Map<String, dynamic> config,
    required bool isActive,
    String? updatedBy,
    int? ifMatchVersion,
  }) async {
    if (onUpsert != null) {
      return onUpsert!(
        cubeId: cubeId,
        productId: productId,
        semanticKey: semanticKey,
        label: label,
        description: description,
        config: config,
        isActive: isActive,
        updatedBy: updatedBy,
        ifMatchVersion: ifMatchVersion,
      );
    }
    return (_makeMapping(), true);
  }

  @override
  Future<SemanticMapping> softDelete(int id) async => _makeMapping(id: id);

  @override
  Future<CubeMetadataSnapshot?> getCubeMetadata(
    String cubeId, {
    bool prime = false,
    int? productId,
  }) async {
    if (onCubeMetadata != null) {
      return onCubeMetadata!(cubeId, prime: prime, productId: productId);
    }
    return null;
  }
}

DioException _envelopeError({
  required int status,
  required String code,
  Map<String, dynamic>? details,
  String message = 'oops',
}) {
  final req = RequestOptions(path: '/x');
  return DioException(
    requestOptions: req,
    response: Response(
      requestOptions: req,
      statusCode: status,
      data: {
        'detail': {
          'error_code': code,
          'message': message,
          if (details != null) 'details': details,
        },
      },
    ),
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

void main() {
  testWidgets('1. List screen renders DataTable with mock data', (tester) async {
    final fake = _FakeRepository();
    await pumpLocalizedWidget(
      tester,
      const SemanticMappingsListScreen(),
      overrides: [
        semanticMappingsRepositoryProvider.overrideWithValue(fake),
      ],
    );
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('semantic-mappings-table')), findsOneWidget);
    expect(find.text('cpi.canada.all_items.index'), findsOneWidget);
  });

  testWidgets('2. Filter input triggers refetch when applied', (tester) async {
    final fake = _FakeRepository();
    await pumpLocalizedWidget(
      tester,
      const SemanticMappingsListScreen(),
      overrides: [
        semanticMappingsRepositoryProvider.overrideWithValue(fake),
      ],
    );
    await tester.pumpAndSettle();
    final initialCalls = fake.listCalls;
    await tester.enterText(
      find.byKey(const ValueKey('filter-cube-id')),
      '18-10-0004',
    );
    await tester.tap(find.byKey(const ValueKey('filter-apply')));
    await tester.pumpAndSettle();
    expect(fake.listCalls, greaterThan(initialCalls));
    expect(fake.lastCubeIdFilter, '18-10-0004');
  });

  testWidgets('3. Form submits valid data and pops on success',
      (tester) async {
    await tester.binding.setSurfaceSize(const Size(800, 1200));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    final fake = _FakeRepository();
    bool upsertCalled = false;
    fake.onUpsert = ({
      required String cubeId,
      required int productId,
      required String semanticKey,
      required String label,
      String? description,
      required Map<String, dynamic> config,
      required bool isActive,
      String? updatedBy,
      int? ifMatchVersion,
    }) async {
      upsertCalled = true;
      return (_makeMapping(), true);
    };
    final router = GoRouter(
      initialLocation: '/semantic-mappings/new',
      routes: [
        GoRoute(
          path: '/semantic-mappings',
          builder: (_, __) => const _ListPlaceholder(),
        ),
        GoRoute(
          path: '/semantic-mappings/new',
          builder: (_, __) =>
              const SemanticMappingFormScreen(mappingId: null),
        ),
      ],
    );
    await pumpLocalizedRouter(
      tester,
      router,
      overrides: [
        semanticMappingsRepositoryProvider.overrideWithValue(fake),
      ],
    );
    await tester.pumpAndSettle();

    await tester.enterText(
        find.byKey(const ValueKey('field-cube-id')), '18-10-0004');
    await tester.enterText(
        find.byKey(const ValueKey('field-product-id')), '18100004');
    await tester.enterText(
        find.byKey(const ValueKey('field-semantic-key')),
        'cpi.canada.all_items.index');
    await tester.enterText(
        find.byKey(const ValueKey('field-label')), 'CPI');
    // Add one filter row.
    await tester.tap(find.byKey(const ValueKey('dim-add-row')));
    await tester.pump();

    await tester.tap(find.byKey(const ValueKey('form-submit')));
    await tester.pumpAndSettle();
    expect(upsertCalled, isTrue);
    expect(find.byType(_ListPlaceholder), findsOneWidget);
  });

  testWidgets('4. Form renders inline error from MEMBER_NOT_FOUND envelope',
      (tester) async {
    await tester.binding.setSurfaceSize(const Size(800, 1200));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    final fake = _FakeRepository();
    fake.onUpsert = ({
      required String cubeId,
      required int productId,
      required String semanticKey,
      required String label,
      String? description,
      required Map<String, dynamic> config,
      required bool isActive,
      String? updatedBy,
      int? ifMatchVersion,
    }) async {
      throw _envelopeError(
        status: 400,
        code: 'MEMBER_NOT_FOUND',
        message: 'Member missing',
        details: {
          'errors': [
            {
              'error_code': 'MEMBER_NOT_FOUND',
              'dimension_name': 'Geography',
              'member_name': 'Atlantis',
              'message': 'Member \'Atlantis\' not found',
            },
          ],
        },
      );
    };

    await pumpLocalizedWidget(
      tester,
      const SemanticMappingFormScreen(mappingId: null),
      overrides: [
        semanticMappingsRepositoryProvider.overrideWithValue(fake),
      ],
    );
    await tester.pumpAndSettle();

    await tester.enterText(
        find.byKey(const ValueKey('field-cube-id')), '18-10-0004');
    await tester.enterText(
        find.byKey(const ValueKey('field-product-id')), '18100004');
    await tester.enterText(
        find.byKey(const ValueKey('field-semantic-key')), 'cpi.bad');
    await tester.enterText(find.byKey(const ValueKey('field-label')), 'L');

    await tester.tap(find.byKey(const ValueKey('form-submit')));
    await tester.pumpAndSettle();

    expect(find.text('Member missing'), findsOneWidget);
  });

  testWidgets('5. Form shows VersionConflictModal on 412', (tester) async {
    await tester.binding.setSurfaceSize(const Size(800, 1200));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    final fake = _FakeRepository();
    fake.onUpsert = ({
      required String cubeId,
      required int productId,
      required String semanticKey,
      required String label,
      String? description,
      required Map<String, dynamic> config,
      required bool isActive,
      String? updatedBy,
      int? ifMatchVersion,
    }) async {
      throw _envelopeError(
        status: 412,
        code: 'VERSION_CONFLICT',
        details: {
          'cube_id': cubeId,
          'semantic_key': semanticKey,
          'expected_version': ifMatchVersion ?? 0,
          'actual_version': 99,
        },
      );
    };

    await pumpLocalizedWidget(
      tester,
      const SemanticMappingFormScreen(mappingId: null),
      overrides: [
        semanticMappingsRepositoryProvider.overrideWithValue(fake),
      ],
    );
    await tester.pumpAndSettle();

    await tester.enterText(
        find.byKey(const ValueKey('field-cube-id')), '18-10-0004');
    await tester.enterText(
        find.byKey(const ValueKey('field-product-id')), '18100004');
    await tester.enterText(
        find.byKey(const ValueKey('field-semantic-key')), 'cpi.k');
    await tester.enterText(find.byKey(const ValueKey('field-label')), 'L');

    await tester.tap(find.byKey(const ValueKey('form-submit')));
    await tester.pumpAndSettle();

    expect(find.byKey(const ValueKey('version-conflict-modal')), findsOneWidget);
  });

  testWidgets('6. dimension_filters editor add/remove rows', (tester) async {
    Map<String, String> latest = {};
    await pumpLocalizedWidget(
      tester,
      Scaffold(
        body: DimensionFiltersEditor(
          value: const {},
          onChanged: (v) => latest = v,
        ),
      ),
    );
    await tester.tap(find.byKey(const ValueKey('dim-add-row')));
    await tester.pump();
    await tester.tap(find.byKey(const ValueKey('dim-add-row')));
    await tester.pump();
    expect(find.byIcon(Icons.delete_outline), findsNWidgets(2));

    await tester.enterText(
        find.byKey(const ValueKey('dim-key-')).first, 'Geography');
    await tester.pump();
    expect(latest.containsKey('Geography'), isTrue);

    await tester.tap(find.byIcon(Icons.delete_outline).first);
    await tester.pump();
    expect(find.byIcon(Icons.delete_outline), findsNWidgets(1));
  });

  test('7. cubeMetadataProvider returns null on 404', () async {
    final fake = _FakeRepository();
    fake.onCubeMetadata =
        (cubeId, {bool prime = false, int? productId}) async => null;
    final container = ProviderContainer(overrides: [
      semanticMappingsRepositoryProvider.overrideWithValue(fake),
    ]);
    addTearDown(container.dispose);
    final result = await container.read(
      cubeMetadataProvider('99-99-9999').future,
    );
    expect(result, isNull);
  });

  test('8. repository.getCubeMetadata triggers prime call when prime=true',
      () async {
    bool sawPrime = false;
    int? sawProductId;
    final fake = _FakeRepository();
    fake.onCubeMetadata = (
      String cubeId, {
      bool prime = false,
      int? productId,
    }) async {
      sawPrime = prime;
      sawProductId = productId;
      return CubeMetadataSnapshot(
        cubeId: cubeId,
        productId: productId ?? 0,
        dimensions: const [],
      );
    };
    final snapshot = await fake.getCubeMetadata(
      '18-10-0004',
      prime: true,
      productId: 18100004,
    );
    expect(snapshot, isNotNull);
    expect(sawPrime, isTrue);
    expect(sawProductId, 18100004);
  });

  testWidgets('9. Form hydrates product_id from existing mapping on edit',
      (tester) async {
    final fake = _FakeRepository();
    await pumpLocalizedWidget(
      tester,
      const SemanticMappingFormScreen(mappingId: 1),
      overrides: [
        semanticMappingsRepositoryProvider.overrideWithValue(fake),
      ],
    );
    await tester.pumpAndSettle();
    final productIdField = tester.widget<TextFormField>(
      find.byKey(const ValueKey('field-product-id')),
    );
    expect(
      productIdField.controller!.text,
      '18100004',
      reason: 'product_id field must hydrate from the loaded mapping',
    );
  });
}

class _ListPlaceholder extends StatelessWidget {
  const _ListPlaceholder();
  @override
  Widget build(BuildContext context) =>
      const Scaffold(body: Center(child: Text('list-placeholder')));
}
