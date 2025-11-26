import 'dart:convert';
import 'dart:developer' as dev;
import 'dart:typed_data';

import 'package:dartantic_ai/dartantic_ai.dart';
import 'package:dartantic_interface/dartantic_interface.dart' show DataPart;
import 'package:flutter_riverpod/flutter_riverpod.dart' as riverpod;
import 'package:json_schema/json_schema.dart';

import 'segmentation_models.dart';

// Provider for the AIService
final aiServiceProvider = riverpod.Provider<AIService>((ref) => AIService());

class AIService {
  late final Agent _agent;

  AIService() {
    // Initialize Agent with Google Provider and API Key from environment
    _agent = Agent.forProvider(
      GoogleProvider(apiKey: const String.fromEnvironment('GEMINI_API_KEY')),
      chatModelName: 'gemini-3-pro-preview',
    );
  }

  Future<
    ({ComicPageSegmentation? segmentation, String? rawResponse, String? error})
  >
  segmentPage(Uint8List imageBytes) async {
    try {
      final prompt =
          'Analyze this comic book page and return the bounding boxes for all panels. '
          'Return coordinates as integers in a 0-1000 scale (ymin, xmin, ymax, xmax).';

      // Define the expected output schema
      final schema = JsonSchema.create({
        'type': 'object',
        'properties': {
          'panels': {
            'type': 'array',
            'items': {
              'type': 'object',
              'properties': {
                'ymin': {
                  'type': 'integer',
                  'description': 'Top Y coordinate (0-1000)',
                },
                'xmin': {
                  'type': 'integer',
                  'description': 'Left X coordinate (0-1000)',
                },
                'ymax': {
                  'type': 'integer',
                  'description': 'Bottom Y coordinate (0-1000)',
                },
                'xmax': {
                  'type': 'integer',
                  'description': 'Right X coordinate (0-1000)',
                },
              },
              'required': ['ymin', 'xmin', 'ymax', 'xmax'],
            },
          },
        },
        'required': ['panels'],
      });

      dev.log('DEBUG: Sending request to Gemini...');

      // Use send() to get the raw text first for debug purposes
      final response = await _agent.send(
        prompt,
        attachments: [DataPart(imageBytes, mimeType: 'image/jpeg')],
        outputSchema: schema,
      );

      final rawText = response.output;

      dev.log('DEBUG: Raw Gemini Response: $rawText');

      try {
        final jsonMap = jsonDecode(rawText);
        final segmentation = ComicPageSegmentation.fromJson(jsonMap);
        return (segmentation: segmentation, rawResponse: rawText, error: null);
      } catch (e) {
        return (
          segmentation: null,
          rawResponse: rawText,
          error: 'Failed to parse JSON: $e',
        );
      }
    } catch (e) {
      return (
        segmentation: null,
        rawResponse: null,
        error: 'AI Request Failed: $e',
      );
    }
  }
}
