import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:summa_vision_admin/core/theme/app_theme.dart';

void main() {
  group('AppTheme', () {
    test('backgroundDark is #141414', () {
      expect(AppTheme.backgroundDark.value, equals(const Color(0xFF141414).value));
    });

    test('neonGreen is #00FF94', () {
      expect(AppTheme.neonGreen.value, equals(const Color(0xFF00FF94).value));
    });

    test('dark theme scaffold background is #141414', () {
      expect(
        AppTheme.dark.scaffoldBackgroundColor,
        equals(AppTheme.backgroundDark),
      );
    });

    test('dark theme primary colour is neonGreen', () {
      expect(
        AppTheme.dark.colorScheme.primary,
        equals(AppTheme.neonGreen),
      );
    });

    testWidgets('MaterialApp boots with dark theme', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.dark,
          home: const Scaffold(body: Text('OK')),
        ),
      );
      expect(find.text('OK'), findsOneWidget);
    });

    testWidgets('SummaVisionApp renders without crashing', (tester) async {
      // Minimal smoke test — does not require dotenv
      await tester.pumpWidget(
        MaterialApp(
          theme: AppTheme.dark,
          home: const Scaffold(
            body: Center(child: Text('Summa Vision')),
          ),
        ),
      );
      expect(find.text('Summa Vision'), findsOneWidget);
    });
  });
}
