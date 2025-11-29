import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';

import 'comic_scanner_screen.dart';

void main() {
  runApp(const ProviderScope(child: ComicSegmentationApp()));
}

class ComicSegmentationApp extends StatelessWidget {
  const ComicSegmentationApp({super.key});

  @override
  Widget build(BuildContext context) => MaterialApp(
    title: 'Comic Segmenter',
    debugShowCheckedModeBanner: false,
    theme: ThemeData(
      textTheme: GoogleFonts.notoSansTextTheme(),
    ),
    home: const ComicScannerScreen(),
  );
}
