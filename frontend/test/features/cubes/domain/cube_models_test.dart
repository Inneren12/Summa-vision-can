import 'package:flutter_test/flutter_test.dart';
import 'package:summa_vision_admin/features/cubes/domain/cube_catalog_entry.dart';
import 'package:summa_vision_admin/features/cubes/domain/cube_search_response.dart';

void main() {
  group('CubeCatalogEntry', () {
    const sampleJson = <String, dynamic>{
      'product_id': '13-10-0888-01',
      'title_en': 'New housing price index, monthly',
      'title_fr': 'Indice des prix des logements neufs, mensuel',
      'subject_code': '18',
      'subject_en': 'Prices and price indexes',
      'survey_en': 'New Housing Price Index',
      'frequency': 'Monthly',
      'start_date': '1981-01-01',
      'end_date': '2024-12-01',
      'archive_status': false,
    };

    test('fromJson parses snake_case JSON into camelCase Dart fields', () {
      final entry = CubeCatalogEntry.fromJson(sampleJson);

      expect(entry.productId, '13-10-0888-01');
      expect(entry.titleEn, 'New housing price index, monthly');
      expect(entry.titleFr, 'Indice des prix des logements neufs, mensuel');
      expect(entry.subjectCode, '18');
      expect(entry.subjectEn, 'Prices and price indexes');
      expect(entry.surveyEn, 'New Housing Price Index');
      expect(entry.frequency, 'Monthly');
      expect(entry.startDate, '1981-01-01');
      expect(entry.endDate, '2024-12-01');
      expect(entry.archiveStatus, false);
    });

    test('toJson serializes to snake_case keys', () {
      final entry = CubeCatalogEntry.fromJson(sampleJson);
      final json = entry.toJson();

      expect(json['product_id'], '13-10-0888-01');
      expect(json['title_en'], 'New housing price index, monthly');
      expect(json['title_fr'], isNotNull);
      expect(json['subject_code'], '18');
      expect(json['subject_en'], 'Prices and price indexes');
      expect(json['survey_en'], 'New Housing Price Index');
      expect(json['frequency'], 'Monthly');
      expect(json['start_date'], '1981-01-01');
      expect(json['end_date'], '2024-12-01');
      expect(json['archive_status'], false);
    });

    test('archiveStatus defaults to false when absent', () {
      final minimal = <String, dynamic>{
        'product_id': '99-99-0001-01',
        'title_en': 'Test cube',
        'subject_code': '01',
        'subject_en': 'Subject',
        'frequency': 'Annual',
      };
      final entry = CubeCatalogEntry.fromJson(minimal);
      expect(entry.archiveStatus, false);
      expect(entry.titleFr, isNull);
      expect(entry.surveyEn, isNull);
      expect(entry.startDate, isNull);
      expect(entry.endDate, isNull);
    });
  });

  group('CubeSearchResponse', () {
    test('fromJson parses full response with items array', () {
      final json = <String, dynamic>{
        'items': [
          {
            'product_id': '13-10-0888-01',
            'title_en': 'Housing index',
            'subject_code': '18',
            'subject_en': 'Prices',
            'frequency': 'Monthly',
          },
          {
            'product_id': '14-10-0287-01',
            'title_en': 'Labour force',
            'subject_code': '14',
            'subject_en': 'Labour',
            'frequency': 'Monthly',
          },
        ],
        'total': 42,
      };

      final response = CubeSearchResponse.fromJson(json);

      expect(response.items.length, 2);
      expect(response.total, 42);
      expect(response.items[0].productId, '13-10-0888-01');
      expect(response.items[1].titleEn, 'Labour force');
    });

    test('fromJson handles empty items list', () {
      final json = <String, dynamic>{
        'items': <dynamic>[],
        'total': 0,
      };

      final response = CubeSearchResponse.fromJson(json);
      expect(response.items, isEmpty);
      expect(response.total, 0);
    });
  });
}
