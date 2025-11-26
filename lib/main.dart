import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'comic_scanner_screen.dart';

void main() {
  runApp(const ProviderScope(child: ComicSegmentationApp()));
}

class ComicSegmentationApp extends StatelessWidget {
  const ComicSegmentationApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Comic Segmenter',
      debugShowCheckedModeBanner: false,
      home: const ComicScannerScreen(),
    );
  }
}
