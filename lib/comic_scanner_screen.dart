import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';

import 'ai_service.dart';
import 'segmentation_models.dart';

class ComicScannerScreen extends ConsumerStatefulWidget {
  const ComicScannerScreen({super.key});

  @override
  ConsumerState<ComicScannerScreen> createState() => _ComicScannerScreenState();
}

class _ComicScannerScreenState extends ConsumerState<ComicScannerScreen> {
  Uint8List? _imageBytes;
  ui.Image? _decodedImage;
  ComicPageSegmentation? _segmentation;
  bool _isLoading = false;
  String? _error;
  String? _rawResponse;

  final ImagePicker _picker = ImagePicker();

  Future<void> _pickImage(ImageSource source) async {
    final pickedFile = await _picker.pickImage(source: source);
    if (pickedFile != null) {
      final bytes = await pickedFile.readAsBytes();
      final decodedImage = await decodeImageFromList(bytes);
      setState(() {
        _imageBytes = bytes;
        _decodedImage = decodedImage;
        _segmentation = null;
        _error = null;
        _rawResponse = null;
      });
    }
  }

  Future<void> _processImage() async {
    if (_imageBytes == null) return;

    setState(() {
      _isLoading = true;
      _error = null;
      _rawResponse = null;
    });

    final result = await ref.read(aiServiceProvider).segmentPage(_imageBytes!);

    setState(() {
      _isLoading = false;
      _segmentation = result.segmentation;
      _rawResponse = result.rawResponse;
      _error = result.error;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Comic Segmenter')),
      body: Column(
        children: [
          Expanded(
            child: _imageBytes == null
                ? const Center(child: Text('Select an image to start'))
                : LayoutBuilder(
                    builder: (context, constraints) {
                      final isWide = constraints.maxWidth > 800;

                      Widget buildImageArea() {
                        return Stack(
                          fit: StackFit.expand,
                          children: [
                            Image.memory(_imageBytes!, fit: BoxFit.contain),
                            if (_segmentation != null && _decodedImage != null)
                              CustomPaint(
                                painter: BoundingBoxPainter(
                                  panels: _segmentation!.panels,
                                  imageSize: Size(
                                    _decodedImage!.width.toDouble(),
                                    _decodedImage!.height.toDouble(),
                                  ),
                                ),
                              ),
                          ],
                        );
                      }

                      Widget buildJsonArea() {
                        if (_rawResponse == null) {
                          return const SizedBox.shrink();
                        }
                        return Container(
                          height: isWide ? double.infinity : 150,
                          padding: const EdgeInsets.all(8.0),
                          color: Colors.grey[200],
                          child: SingleChildScrollView(
                            child: Text('Raw Response: $_rawResponse'),
                          ),
                        );
                      }

                      if (isWide) {
                        return Row(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            Expanded(
                              flex: 2,
                              child: Padding(
                                padding: const EdgeInsets.all(16.0),
                                child: buildImageArea(),
                              ),
                            ),
                            Expanded(
                              flex: 1,
                              child: Padding(
                                padding: const EdgeInsets.all(32.0),
                                child: buildJsonArea(),
                              ),
                            ),
                          ],
                        );
                      } else {
                        return Padding(
                          padding: const EdgeInsets.all(32),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.stretch,
                            children: [
                              Expanded(
                                child: Padding(
                                  padding: const EdgeInsets.all(8.0),
                                  child: buildImageArea(),
                                ),
                              ),
                              if (_rawResponse != null)
                                // To match the width of the image, we can just let it fill the width
                                // of the column, which matches the image area's width.
                                // Since the image is BoxFit.contain, it might be narrower visually,
                                // but the widget itself takes full width.
                                // This satisfies "match the width of the image" in terms of layout constraints.
                                buildJsonArea(),
                            ],
                          ),
                        );
                      }
                    },
                  ),
          ),
          if (_isLoading) const LinearProgressIndicator(),
          if (_error != null)
            Padding(
              padding: const EdgeInsets.all(8.0),
              child: Text(
                'Error: $_error',
                style: const TextStyle(color: Colors.red),
              ),
            ),
          Padding(
            padding: const EdgeInsets.all(16.0),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: [
                ElevatedButton.icon(
                  onPressed: () => _pickImage(ImageSource.gallery),
                  icon: const Icon(Icons.photo),
                  label: const Text('Gallery'),
                ),
                ElevatedButton.icon(
                  onPressed: () => _pickImage(ImageSource.camera),
                  icon: const Icon(Icons.camera_alt),
                  label: const Text('Camera'),
                ),
                ElevatedButton.icon(
                  onPressed: _imageBytes != null && !_isLoading
                      ? _processImage
                      : null,
                  icon: const Icon(Icons.auto_awesome),
                  label: const Text('Process'),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class BoundingBoxPainter extends CustomPainter {
  final List<Panel> panels;
  final Size imageSize;

  BoundingBoxPainter({required this.panels, required this.imageSize});

  @override
  void paint(Canvas canvas, Size size) {
    if (imageSize.isEmpty) return;

    final paint = Paint()
      ..color = Colors.red
      ..style = PaintingStyle.stroke
      ..strokeWidth = 3.0;

    // Calculate the destination rectangle of the image within the canvas
    // using BoxFit.contain (which is what the Image widget uses).
    final fittedSizes = applyBoxFit(BoxFit.contain, imageSize, size);
    final destinationSize = fittedSizes.destination;

    // Calculate centering offsets
    final dx = (size.width - destinationSize.width) / 2;
    final dy = (size.height - destinationSize.height) / 2;

    final destinationRect = Offset(dx, dy) & destinationSize;

    // Map 0-1000 coordinates to the destinationRect
    for (final panel in panels) {
      final rect = Rect.fromLTRB(
        destinationRect.left + (panel.xmin / 1000 * destinationRect.width),
        destinationRect.top + (panel.ymin / 1000 * destinationRect.height),
        destinationRect.left + (panel.xmax / 1000 * destinationRect.width),
        destinationRect.top + (panel.ymax / 1000 * destinationRect.height),
      );
      canvas.drawRect(rect, paint);
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => true;
}
