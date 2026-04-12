import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/dio_client.dart';
import '../domain/kpi_data.dart';

/// Repository for fetching KPI dashboard data.
class KPIRepository {
  KPIRepository(this._dio);

  final Dio _dio;

  /// Fetch aggregated KPI data for the given period.
  Future<KPIData> getKPI({int days = 30}) async {
    final response = await _dio.get<Map<String, dynamic>>(
      '/api/v1/admin/kpi',
      queryParameters: {'days': days},
    );
    return KPIData.fromJson(response.data!);
  }
}

/// Riverpod provider for [KPIRepository].
final kpiRepositoryProvider = Provider<KPIRepository>(
  (ref) => KPIRepository(ref.watch(dioProvider)),
);
