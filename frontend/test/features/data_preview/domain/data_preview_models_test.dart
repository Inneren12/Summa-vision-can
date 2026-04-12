import 'package:flutter_test/flutter_test.dart';
import 'package:summa_vision_admin/features/data_preview/domain/data_preview_response.dart';
import 'package:summa_vision_admin/features/data_preview/domain/preview_filter.dart';

void main() {
  group('DataPreviewResponse', () {
    test('fromJson parses full response with snake_case keys', () {
      final json = <String, dynamic>{
        'storage_key': 'statcan/processed/13-10-0888-01/2024-12-15.parquet',
        'rows': 48520,
        'columns': 4,
        'column_names': ['REF_DATE', 'GEO', 'VALUE', 'SCALAR_ID'],
        'data': [
          {
            'REF_DATE': '2024-01',
            'GEO': 'Canada',
            'VALUE': 156.2,
            'SCALAR_ID': 0,
          },
          {
            'REF_DATE': '2024-02',
            'GEO': 'Ontario',
            'VALUE': null,
            'SCALAR_ID': 0,
          },
        ],
      };

      final response = DataPreviewResponse.fromJson(json);

      expect(response.storageKey,
          'statcan/processed/13-10-0888-01/2024-12-15.parquet');
      expect(response.rows, 48520);
      expect(response.columns, 4);
      expect(response.columnNames, ['REF_DATE', 'GEO', 'VALUE', 'SCALAR_ID']);
      expect(response.data.length, 2);
      expect(response.data[0]['GEO'], 'Canada');
      expect(response.data[1]['VALUE'], isNull);
    });

    test('fromJson handles data rows containing null values', () {
      final json = <String, dynamic>{
        'storage_key': 'test/key.parquet',
        'rows': 2,
        'columns': 1,
        'column_names': ['VALUE'],
        'data': [
          {'VALUE': null},
          {'VALUE': 42.0},
        ],
      };

      final response = DataPreviewResponse.fromJson(json);

      expect(response.data[0]['VALUE'], isNull);
      expect(response.data[1]['VALUE'], 42.0);
    });

    test('toJson serializes to snake_case keys', () {
      const response = DataPreviewResponse(
        storageKey: 'test/key.parquet',
        rows: 500,
        columns: 1,
        columnNames: ['A'],
        data: [
          {'A': 'hello'}
        ],
      );

      final json = response.toJson();

      expect(json['storage_key'], 'test/key.parquet');
      expect(json['rows'], 500);
      expect(json['columns'], 1);
      expect(json['column_names'], ['A']);
      expect(json['data'], isList);
    });
  });

  group('PreviewFilter', () {
    test('default constructor has all null fields', () {
      const filter = PreviewFilter();

      expect(filter.geoFilter, isNull);
      expect(filter.dateFromFilter, isNull);
      expect(filter.dateToFilter, isNull);
      expect(filter.searchText, isNull);
    });

    test('copyWith creates modified copy', () {
      const filter = PreviewFilter();
      final modified = filter.copyWith(geoFilter: 'Ontario');

      expect(modified.geoFilter, 'Ontario');
      expect(modified.dateFromFilter, isNull);
    });

    test('equality works for identical filters', () {
      const a = PreviewFilter(geoFilter: 'Canada');
      const b = PreviewFilter(geoFilter: 'Canada');

      expect(a, equals(b));
    });
  });
}
