import 'dart:async';

import 'package:google_fonts/google_fonts.dart';

/// Global test configuration — runs before every test file.
///
/// Disables Google Fonts runtime fetching so tests do not attempt
/// HTTP calls (which the Flutter test harness blocks in CI).
/// Fonts fall back to system defaults — tests verify token values
/// and theme structure, not actual font rendering.
Future<void> testExecutable(FutureOr<void> Function() testMain) async {
  GoogleFonts.config.allowRuntimeFetching = false;
  await testMain();
}
