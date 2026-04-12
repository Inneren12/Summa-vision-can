import 'package:flutter_test/flutter_test.dart';
import 'package:summa_vision_admin/features/data_preview/domain/data_preview_response.dart';
import 'package:summa_vision_admin/features/data_preview/domain/preview_filter.dart';

void main() {
  group('ColumnSchema', () {
    test('fromJson parses name and dtype', () {
      final json = {'name': 'VALUE', 'dtype': 'float64'};
      final col = ColumnSchema.fromJson(json);

      expect(col.name, 'VALUE');
      expect(col.dtype, 'float64');
    });

    test('toJson round-trips correctly', () {
      final col = const ColumnSchema(name: 'GEO', dtype: 'str');
      final json = col.toJson();

      expect(json['name'], 'GEO');
      expect(json['dtype'], 'str');
    });
  });

  group('DataPreviewResponse', () {
    test('fromJson parses full response with snake_case keys', () {
      final json = <String, dynamic>{
        'columns': [
          {'name': 'REF_DATE', 'dtype': 'str'},
          {'name': 'GEO', 'dtype': 'str'},
          {'name': 'VALUE', 'dtype': 'float64'},
          {'name': 'SCALAR_ID', 'dtype': 'int64'},
        ],
        'rows': [
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
        'total_rows': 48520,
        'returned_rows': 100,
      };

      final response = DataPreviewResponse.fromJson(json);

      expect(response.columns.length, 4);
      expect(response.columns[0].name, 'REF_DATE');
      expect(response.columns[2].dtype, 'float64');
      expect(response.rows.length, 2);
      expect(response.rows[0]['GEO'], 'Canada');
      expect(response.rows[1]['VALUE'], isNull);
      expect(response.totalRows, 48520);
      expect(response.returnedRows, 100);
    });

    test('fromJson handles rows containing null values', () {
      final json = <String, dynamic>{
        'columns': [
          {'name': 'VALUE', 'dtype': 'float64'},
        ],
        'rows': [
          {'VALUE': null},
          {'VALUE': 42.0},
        ],
        'total_rows': 2,
        'returned_rows': 2,
      };

      final response = DataPreviewResponse.fromJson(json);

      expect(response.rows[0]['VALUE'], isNull);
      expect(response.rows[1]['VALUE'], 42.0);
    });

    test('toJson serializes to snake_case keys', () {
      const response = DataPreviewResponse(
        columns: [ColumnSchema(name: 'A', dtype: 'str')],
        rows: [
          {'A': 'hello'}
        ],
        totalRows: 500,
        returnedRows: 100,
      );

      final json = response.toJson();

      expect(json['total_rows'], 500);
      expect(json['returned_rows'], 100);
      expect(json['columns'], isList);
      expect(json['rows'], isList);
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
