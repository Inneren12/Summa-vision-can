import 'dart:convert';
import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:summa_vision_admin/features/queue/domain/content_brief.dart';

void main() {
  group('ContentBrief schema drift detection', () {
    late Map<String, dynamic> backendSchema;

    setUpAll(() {
      // Load the exported Python Pydantic schema
      // Path is relative to the frontend/ directory where flutter test runs
      final schemaFile = File(
        '../backend/schemas/publication_response.schema.json',
      );
      if (!schemaFile.existsSync()) {
        fail(
          'Schema file not found: ${schemaFile.path}\n'
          'Run: cd backend && python scripts/export_schemas.py',
        );
      }
      backendSchema =
          jsonDecode(schemaFile.readAsStringSync()) as Map<String, dynamic>;
    });

    test('backend schema has properties section', () {
      expect(backendSchema.containsKey('properties'), isTrue);
    });

    test('Dart ContentBrief contains all backend required fields', () {
      final backendFields =
          (backendSchema['properties'] as Map<String, dynamic>).keys.toSet();

      // Create a sample Dart model and check its JSON keys
      final sample = ContentBrief(
        id: 1,
        headline: 'Test',
        chartType: 'BAR',
        viralityScore: 8.5,
        status: 'DRAFT',
        createdAt: '2026-01-01T00:00:00Z',
      );
      final dartFields = sample.toJson().keys.toSet();

      // Map snake_case backend keys to Dart camelCase via @JsonKey
      // The toJson() output uses snake_case because of @JsonKey(name: ...)
      for (final backendField in backendFields) {
        expect(
          dartFields.contains(backendField),
          isTrue,
          reason:
              'Backend field "$backendField" missing from Dart ContentBrief.toJson()',
        );
      }
    });

    test('virality_score is numeric in backend schema', () {
      final props = backendSchema['properties'] as Map<String, dynamic>;
      final scoreField = props['virality_score'] as Map<String, dynamic>;
      // Backend uses anyOf [number, null] since virality_score is Optional
      final anyOf = scoreField['anyOf'];
      final isNumeric =
          scoreField['type'] == 'number' ||
          scoreField['type'] == 'integer' ||
          (anyOf is List &&
              anyOf.any(
                (t) =>
                    t is Map &&
                    (t['type'] == 'number' || t['type'] == 'integer'),
              ));
      expect(isNumeric, isTrue);
    });

    test('id is integer in backend schema', () {
      final props = backendSchema['properties'] as Map<String, dynamic>;
      final idField = props['id'] as Map<String, dynamic>;
      expect(idField['type'], equals('integer'));
    });

    test('headline is string in backend schema', () {
      final props = backendSchema['properties'] as Map<String, dynamic>;
      final headlineField = props['headline'] as Map<String, dynamic>;
      expect(headlineField['type'], equals('string'));
    });

    test('Dart toJson uses snake_case keys matching backend', () {
      final sample = ContentBrief(
        id: 1,
        headline: 'Test',
        chartType: 'LINE',
        viralityScore: 7.0,
        status: 'DRAFT',
        createdAt: '2026-01-01T00:00:00Z',
      );
      final json = sample.toJson();

      expect(json.containsKey('id'), isTrue);
      expect(json.containsKey('headline'), isTrue);
      expect(json.containsKey('chart_type'), isTrue);
      expect(json.containsKey('virality_score'), isTrue);
      expect(json.containsKey('status'), isTrue);
      expect(json.containsKey('created_at'), isTrue);
    });
  });
}
