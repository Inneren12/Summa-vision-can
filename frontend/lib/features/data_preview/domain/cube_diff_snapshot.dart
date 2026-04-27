class CubeDiffSnapshot {
  const CubeDiffSnapshot({
    required this.columnNames,
    required this.data,
    required this.savedAtMillis,
  });

  final List<String> columnNames;
  final List<Map<String, dynamic>> data;
  final int savedAtMillis;

  factory CubeDiffSnapshot.fromJson(Map<String, dynamic> json) {
    return CubeDiffSnapshot(
      columnNames: (json['columnNames'] as List<dynamic>).cast<String>(),
      data: (json['data'] as List<dynamic>)
          .map((e) => Map<String, dynamic>.from(e as Map))
          .toList(),
      savedAtMillis: (json['savedAtMillis'] as num).toInt(),
    );
  }

  Map<String, dynamic> toJson() => {
        'columnNames': columnNames,
        'data': data,
        'savedAtMillis': savedAtMillis,
      };
}
