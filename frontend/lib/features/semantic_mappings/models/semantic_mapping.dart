/// Phase 3.1b semantic-mapping models — hand-rolled (no codegen).
///
/// Mirrors the backend ``SemanticMappingResponse`` shape on the wire.
/// Lives outside the freezed/codegen tree so the admin app can consume
/// the new endpoints without an extra build_runner pass.

class SemanticMappingConfig {
  const SemanticMappingConfig({
    required this.dimensionFilters,
    required this.measure,
    required this.unit,
    required this.frequency,
    required this.supportedMetrics,
    this.defaultGeo,
    this.notes,
  });

  final Map<String, String> dimensionFilters;
  final String measure;
  final String unit;
  final String frequency;
  final List<String> supportedMetrics;
  final String? defaultGeo;
  final String? notes;

  factory SemanticMappingConfig.fromJson(Map<String, dynamic> json) {
    final rawFilters = json['dimension_filters'];
    final filters = <String, String>{};
    if (rawFilters is Map) {
      rawFilters.forEach((key, value) {
        if (key is String && value is String) {
          filters[key] = value;
        }
      });
    }
    final metrics = (json['supported_metrics'] as List?)
            ?.whereType<String>()
            .toList(growable: false) ??
        const <String>[];
    return SemanticMappingConfig(
      dimensionFilters: filters,
      measure: json['measure'] as String,
      unit: json['unit'] as String,
      frequency: json['frequency'] as String,
      supportedMetrics: metrics,
      defaultGeo: json['default_geo'] as String?,
      notes: json['notes'] as String?,
    );
  }

  Map<String, dynamic> toJson() => {
        'dimension_filters': dimensionFilters,
        'measure': measure,
        'unit': unit,
        'frequency': frequency,
        'supported_metrics': supportedMetrics,
        if (defaultGeo != null) 'default_geo': defaultGeo,
        if (notes != null) 'notes': notes,
      };

  SemanticMappingConfig copyWith({
    Map<String, String>? dimensionFilters,
    String? measure,
    String? unit,
    String? frequency,
    List<String>? supportedMetrics,
    String? defaultGeo,
    String? notes,
  }) {
    return SemanticMappingConfig(
      dimensionFilters: dimensionFilters ?? this.dimensionFilters,
      measure: measure ?? this.measure,
      unit: unit ?? this.unit,
      frequency: frequency ?? this.frequency,
      supportedMetrics: supportedMetrics ?? this.supportedMetrics,
      defaultGeo: defaultGeo ?? this.defaultGeo,
      notes: notes ?? this.notes,
    );
  }
}

class SemanticMapping {
  const SemanticMapping({
    required this.id,
    required this.cubeId,
    required this.semanticKey,
    required this.label,
    this.description,
    required this.config,
    required this.isActive,
    required this.version,
    required this.createdAt,
    required this.updatedAt,
    this.updatedBy,
  });

  final int id;
  final String cubeId;
  final String semanticKey;
  final String label;
  final String? description;
  final SemanticMappingConfig config;
  final bool isActive;
  final int version;
  final DateTime createdAt;
  final DateTime updatedAt;
  final String? updatedBy;

  factory SemanticMapping.fromJson(Map<String, dynamic> json) {
    return SemanticMapping(
      id: (json['id'] as num).toInt(),
      cubeId: json['cube_id'] as String,
      semanticKey: json['semantic_key'] as String,
      label: json['label'] as String,
      description: json['description'] as String?,
      config: SemanticMappingConfig.fromJson(
        Map<String, dynamic>.from(json['config'] as Map),
      ),
      isActive: json['is_active'] as bool,
      version: (json['version'] as num).toInt(),
      createdAt: DateTime.parse(json['created_at'] as String),
      updatedAt: DateTime.parse(json['updated_at'] as String),
      updatedBy: json['updated_by'] as String?,
    );
  }
}

class SemanticMappingListPage {
  const SemanticMappingListPage({
    required this.items,
    required this.total,
    required this.limit,
    required this.offset,
  });

  final List<SemanticMapping> items;
  final int total;
  final int limit;
  final int offset;

  factory SemanticMappingListPage.fromJson(Map<String, dynamic> json) {
    final items = (json['items'] as List)
        .map((e) => SemanticMapping.fromJson(Map<String, dynamic>.from(e as Map)))
        .toList(growable: false);
    return SemanticMappingListPage(
      items: items,
      total: (json['total'] as num).toInt(),
      limit: (json['limit'] as num).toInt(),
      offset: (json['offset'] as num).toInt(),
    );
  }
}

/// Cached cube metadata snapshot shape — minimal subset used by the form.
class CubeMetadataSnapshot {
  const CubeMetadataSnapshot({
    required this.cubeId,
    required this.productId,
    required this.dimensions,
    this.titleEn,
    this.titleFr,
  });

  final String cubeId;
  final int productId;
  final List<CubeDimension> dimensions;
  final String? titleEn;
  final String? titleFr;

  factory CubeMetadataSnapshot.fromJson(Map<String, dynamic> json) {
    final rawDims = json['dimensions'];
    final dims = <CubeDimension>[];
    if (rawDims is Map && rawDims['dimensions'] is List) {
      for (final d in rawDims['dimensions'] as List) {
        if (d is Map) {
          dims.add(
            CubeDimension.fromJson(Map<String, dynamic>.from(d)),
          );
        }
      }
    }
    return CubeMetadataSnapshot(
      cubeId: json['cube_id'] as String,
      productId: (json['product_id'] as num).toInt(),
      dimensions: dims,
      titleEn: json['cube_title_en'] as String?,
      titleFr: json['cube_title_fr'] as String?,
    );
  }
}

class CubeDimension {
  const CubeDimension({
    required this.nameEn,
    required this.memberNamesEn,
  });

  final String nameEn;
  final List<String> memberNamesEn;

  factory CubeDimension.fromJson(Map<String, dynamic> json) {
    final members = <String>[];
    if (json['members'] is List) {
      for (final m in json['members'] as List) {
        if (m is Map && m['name_en'] is String) {
          members.add(m['name_en'] as String);
        }
      }
    }
    return CubeDimension(
      nameEn: (json['name_en'] as String?) ?? '',
      memberNamesEn: members,
    );
  }
}
