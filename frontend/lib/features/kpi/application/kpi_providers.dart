import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/kpi_repository.dart';
import '../domain/kpi_data.dart';

/// Selected period in days for the KPI dashboard.
final kpiPeriodDaysProvider = StateProvider<int>((ref) => 30);

/// Fetches KPI data for the selected period.
///
/// Auto-disposes when no longer watched. Re-fetches when
/// [kpiPeriodDaysProvider] changes.
final kpiDataProvider = FutureProvider.autoDispose<KPIData>((ref) async {
  final days = ref.watch(kpiPeriodDaysProvider);
  final repo = ref.read(kpiRepositoryProvider);
  return repo.getKPI(days: days);
});
