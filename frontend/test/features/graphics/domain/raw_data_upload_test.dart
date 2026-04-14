import 'package:flutter_test/flutter_test.dart';
import 'package:summa_vision_admin/features/graphics/domain/raw_data_upload.dart';

void main() {
  group('RawDataColumn — JSON serialization', () {
    test('round-trips through toJson / fromJson', () {
      const col = RawDataColumn(name: 'price', dtype: 'float');
      final json = col.toJson();
      expect(json['name'], 'price');
      expect(json['dtype'], 'float');

      final restored = RawDataColumn.fromJson(json);
      expect(restored, col);
    });

    test('default dtype is "str"', () {
      const col = RawDataColumn(name: 'label');
      expect(col.dtype, 'str');
      final json = col.toJson();
      expect(json['dtype'], 'str');
    });

    test('fromJson with missing dtype uses default', () {
      final restored = RawDataColumn.fromJson({'name': 'label'});
      expect(restored.name, 'label');
      expect(restored.dtype, 'str');
    });
  });

  group('GenerateFromDataRequest — JSON serialization', () {
    test('toJson includes all fields in snake_case', () {
      const request = GenerateFromDataRequest(
        data: [
          {'x': 1},
        ],
        columns: [RawDataColumn(name: 'x', dtype: 'int')],
        chartType: 'bar',
        title: 'Test',
        category: 'housing',
      );

      final json = request.toJson();
      expect(json['chart_type'], 'bar');
      expect(json['data'], hasLength(1));
      expect(json['size'], [1200, 900]);
      expect(json['category'], 'housing');
      expect(json['title'], 'Test');
      expect(json['source_label'], 'custom');

      // Verify columns are serialized as a list of maps
      expect(json['columns'], isA<List>());
      expect((json['columns'] as List).first, isA<Map>());

      // Verify camelCase keys are NOT present
      expect(json.containsKey('chartType'), isFalse);
      expect(json.containsKey('sourceLabel'), isFalse);
    });

    test('custom size is preserved', () {
      const request = GenerateFromDataRequest(
        data: [
          {'x': 1},
        ],
        columns: [RawDataColumn(name: 'x')],
        chartType: 'line',
        title: 'T',
        category: 'housing',
        size: [1600, 900],
      );
      expect(request.toJson()['size'], [1600, 900]);
    });

    test('fromJson accepts all backend-emitted fields', () {
      final json = {
        'data': [
          {'x': 1},
          {'x': 2},
        ],
        'columns': [
          {'name': 'x', 'dtype': 'int'},
        ],
        'chart_type': 'line',
        'title': 'My Chart',
        'size': [1080, 1080],
        'category': 'housing',
        'source_label': 'survey',
      };

      final parsed = GenerateFromDataRequest.fromJson(json);
      expect(parsed.chartType, 'line');
      expect(parsed.sourceLabel, 'survey');
      expect(parsed.size, [1080, 1080]);
      expect(parsed.data, hasLength(2));
      expect(parsed.columns.single.dtype, 'int');
    });
  });
}
