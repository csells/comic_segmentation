# Comic Page Segmentation

A Flutter application that uses Google's Gemini AI to automatically detect and
segment panels in comic book pages.

## Features

-   **AI-Powered Segmentation**: Uses the `gemini-3-pro-preview` model via
    `dartantic_ai` to analyze comic pages.
-   **Visual Feedback**: Draws red bounding boxes around detected panels
    overlaid on the original image.
-   **Responsive Design**:
    -   **Wide Screens (>800px)**: Displays the image and raw JSON response
        side-by-side.
    -   **Narrow Screens**: Stacks the image and JSON response vertically.
-   **Developer Tools**: Always displays the raw JSON response from the LLM for
    debugging and verification.
-   **Cross-Platform**: Supports macOS, Windows, Linux, and Web (using
    `Image.memory` for compatibility).

## Setup

1.  **Get an API Key**: You need a valid Gemini API key from Google AI Studio.
2.  **Clone the Repository**:
    ```bash
    git clone <repository-url>
    cd plasma-disk
    ```
3.  **Install Dependencies**:
    ```bash
    flutter pub get
    ```

## Running the App

To run the application, you must provide your Gemini API key using the
`--dart-define` flag.

### VS Code
Update your `.vscode/launch.json` configuration:

```json
{
    "name": "plasma-disk",
    "request": "launch",
    "type": "dart",
    "args": [
        "--dart-define=GEMINI_API_KEY=${env:GEMINI_API_KEY}"
    ]
}
```

### Terminal
```bash
flutter run --dart-define=GEMINI_API_KEY=YOUR_ACTUAL_API_KEY
```

## Project Structure

The project follows a simple, flat structure in `lib/`:

-   `main.dart`: Entry point of the application.
-   `comic_scanner_screen.dart`: Main UI implementation, handling image picking,
    display, and responsive layout.
-   `ai_service.dart`: Handles communication with the Gemini API using
    `dartantic_ai`.
-   `segmentation_models.dart`: Data models for parsing the AI response.
