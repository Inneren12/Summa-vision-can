import 'dart:async';

import 'package:google_fonts/google_fonts.dart';

/// Global test configuration — runs before every test file.
///
/// Enables Google Fonts runtime fetching so [buildSummaTheme] can
/// resolve font families without bundled assets. The Flutter test
/// harness tolerates this when fonts gracefully fall back.
Future<void> testExecutable(FutureOr<void> Function() testMain) async {
  GoogleFonts.config.allowRuntimeFetching = true;
  await testMain();
}
