import 'dart:async';

import 'package:google_fonts/google_fonts.dart';

/// Global test configuration — runs before every test file.
///
/// Disables Google Fonts runtime fetching so tests do not make
/// real HTTP requests (which the Flutter test harness blocks).
Future<void> testExecutable(FutureOr<void> Function() testMain) async {
  GoogleFonts.config.allowRuntimeFetching = false;
  await testMain();
}
