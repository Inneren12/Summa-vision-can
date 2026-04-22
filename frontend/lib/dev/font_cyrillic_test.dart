import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class FontCyrillicTest extends StatelessWidget {
  const FontCyrillicTest({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF141414),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Display (Manrope): Ключевой показатель',
              style: GoogleFonts.manrope(
                fontSize: 24,
                color: Colors.white,
              ),
            ),
            const SizedBox(height: 12),
            Text(
              'Body (DM Sans): Добавить в очередь публикаций',
              style: GoogleFonts.dmSans(
                fontSize: 16,
                color: Colors.white,
              ),
            ),
            const SizedBox(height: 12),
            Text(
              'Data (JetBrains Mono): ОБЯЗ · 42 · черновик',
              style: GoogleFonts.jetBrainsMono(
                fontSize: 14,
                color: Colors.white,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
