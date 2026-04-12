import 'package:flutter_test/flutter_test.dart';
import 'package:summa_vision_admin/features/graphics/domain/chart_constants.dart';
import 'package:summa_vision_admin/features/graphics/domain/generation_result.dart';
import 'package:summa_vision_admin/features/graphics/domain/graphics_generate_request.dart';
import 'package:summa_vision_admin/features/graphics/domain/job_status.dart';

void main() {
  group('GraphicsGenerateRequest — JSON serialization', () {
    test('test_graphics_generate_request_to_json', () {
      const request = GraphicsGenerateRequest(
        dataKey: 'statcan/processed/13-10-0888-01/2024-12-15.parquet',
        chartType: 'line',
        title: 'New Housing Price Index',
        size: [1080, 1080],
        category: 'housing',
        sourceProductId: '13-10-0888-01',
      );

      final json = request.toJson();

      // Assert snake_case keys
      expect(json['data_key'],
          'statcan/processed/13-10-0888-01/2024-12-15.parquet');
      expect(json['chart_type'], 'line');
      expect(json['title'], 'New Housing Price Index');
      expect(json['size'], [1080, 1080]);
      expect(json['category'], 'housing');
      expect(json['source_product_id'], '13-10-0888-01');

      // Verify camelCase keys are NOT present
      expect(json.containsKey('dataKey'), isFalse);
      expect(json.containsKey('chartType'), isFalse);
      expect(json.containsKey('sourceProductId'), isFalse);
    });

    test('serializes without sourceProductId when null', () {
      const request = GraphicsGenerateRequest(
        dataKey: 'test/key.parquet',
        chartType: 'bar',
        title: 'Test',
        size: [1200, 628],
        category: 'inflation',
      );

      final json = request.toJson();
      expect(json['source_product_id'], isNull);
    });
  });

  group('GenerationResult — JSON deserialization', () {
    test('test_generation_result_from_json', () {
      final json = {
        'publication_id': 42,
        'cdn_url_lowres':
            'https://cdn.summa.vision/publications/42/v1/abcd_lowres.png',
        's3_key_highres': 'publications/42/v1/abcd_highres.png',
        'version': 1,
      };

      final result = GenerationResult.fromJson(json);

      expect(result.publicationId, 42);
      expect(result.cdnUrlLowres,
          'https://cdn.summa.vision/publications/42/v1/abcd_lowres.png');
      expect(result.s3KeyHighres, 'publications/42/v1/abcd_highres.png');
      expect(result.version, 1);
    });
  });

  group('JobStatus — JSON deserialization', () {
    test('test_job_status_from_json_with_result', () {
      final json = {
        'job_id': 'abc-123',
        'status': 'success',
        'result_json':
            '{"publication_id":1,"cdn_url_lowres":"https://cdn.example.com/img.png","s3_key_highres":"pub/1/v1/img.png","version":1}',
      };

      final status = JobStatus.fromJson(json);

      expect(status.jobId, 'abc-123');
      expect(status.status, 'success');
      expect(status.resultJson, isNotNull);
      expect(status.resultJson, contains('publication_id'));
      expect(status.isSuccess, isTrue);
      expect(status.isFailed, isFalse);
    });

    test('parses running status with null result_json', () {
      final json = {
        'job_id': 'abc-123',
        'status': 'running',
        'result_json': null,
      };

      final status = JobStatus.fromJson(json);

      expect(status.isRunning, isTrue);
      expect(status.isSuccess, isFalse);
      expect(status.resultJson, isNull);
    });

    test('parses failed status with error_message', () {
      final json = {
        'job_id': 'abc-123',
        'status': 'failed',
        'error_message': 'SVG render error',
      };

      final status = JobStatus.fromJson(json);

      expect(status.isFailed, isTrue);
      expect(status.errorMessage, 'SVG render error');
    });

    test('parses queued status', () {
      final json = {
        'job_id': 'abc-123',
        'status': 'queued',
      };

      final status = JobStatus.fromJson(json);

      expect(status.isQueued, isTrue);
      expect(status.isRunning, isFalse);
    });
  });

  group('ChartType enum', () {
    test('test_chart_type_enum_api_values', () {
      expect(ChartType.line.apiValue, 'line');
      expect(ChartType.bar.apiValue, 'bar');
      expect(ChartType.area.apiValue, 'area');
      expect(ChartType.scatter.apiValue, 'scatter');
      expect(ChartType.stackedBar.apiValue, 'stacked_bar');
    });

    test('display names are human-readable', () {
      expect(ChartType.line.displayName, 'Line Chart');
      expect(ChartType.bar.displayName, 'Bar Chart');
      expect(ChartType.stackedBar.displayName, 'Stacked Bar');
    });

    test('has exactly 5 values', () {
      expect(ChartType.values.length, 5);
    });
  });

  group('SizePreset enum', () {
    test('test_size_preset_dimensions', () {
      expect(SizePreset.instagram.dimensions, [1080, 1080]);
      expect(SizePreset.twitter.dimensions, [1200, 628]);
      expect(SizePreset.reddit.dimensions, [1200, 900]);
    });

    test('display names include aspect ratio', () {
      expect(SizePreset.instagram.displayName, contains('1:1'));
      expect(SizePreset.twitter.displayName, contains('1.91:1'));
      expect(SizePreset.reddit.displayName, contains('4:3'));
    });

    test('has exactly 3 values', () {
      expect(SizePreset.values.length, 3);
    });
  });

  group('BackgroundCategory enum', () {
    test('api values are lowercase', () {
      expect(BackgroundCategory.housing.apiValue, 'housing');
      expect(BackgroundCategory.inflation.apiValue, 'inflation');
      expect(BackgroundCategory.employment.apiValue, 'employment');
      expect(BackgroundCategory.trade.apiValue, 'trade');
      expect(BackgroundCategory.energy.apiValue, 'energy');
      expect(BackgroundCategory.demographics.apiValue, 'demographics');
    });

    test('has exactly 6 values', () {
      expect(BackgroundCategory.values.length, 6);
    });
  });
}
