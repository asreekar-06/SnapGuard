SnapGuard

On-Device Screen Privacy Filter for Screen Sharing

SnapGuard is a working prototype that detects sensitive information displayed on a computer screen and automatically pixelates it in an outgoing preview.

The goal is to prevent sensitive information such as email addresses, phone numbers, API keys, passwords, tokens, and identification numbers from being accidentally exposed during screen sharing.

How It Works

Screen Capture
      ↓
OCR
      ↓
Sensitive Data Detection
      ↓
Bounding Box Detection
      ↓
Pixelation
      ↓
Protected Preview


SnapGuard captures the screen using 'mss', extracts visible text using RapidOCR, checks the detected text against sensitive-data patterns, and pixelates matching regions using OpenCV.

The original screen remains unchanged. The protected version is displayed in the SnapGuard preview window.

Currently Detected:

The prototype includes detection patterns for:

* Email addresses
* Indian phone numbers
* API keys
* Secrets / tokens / passwords
* Long authentication tokens
* Aadhaar-style numbers
* Card numbers

Features:

* Real-time screen capture
* On-device OCR processing
* Pattern-based sensitive information detection
* Automatic pixelation of detected information
* Per-window blur opt-out
* Global blur toggle
* Protected outgoing-feed preview
* No cloud API or external service required at runtime

Controls

| Control          | Action                                        |
| ---------------- | --------------------------------------------- |
| `Ctrl + Alt + B` | Disable blur for the currently focused window |
| `Ctrl + Alt + Q` | Quit SnapGuard                                |
| `O`              | Toggle global blur                            |
| `Q`              | Quit from the preview window                  |

The per-window opt-out automatically resumes protection when focus changes to another window.

Requirements:

* Windows
* Python 3.10+
* OpenCV
* MSS
* NumPy
* RapidOCR ONNX Runtime
* PyWin32
* Keyboard

Install the dependencies with:


pip install -r requirements.txt

Running the Prototype:

Run:

python snapguard.py


A preview window will display the protected screen.

For testing, open Notepad and enter sample sensitive information such as:


Email: test@example.com
Phone: 9876543210
Password: SecretPassword123


SnapGuard should detect and pixelate the sensitive regions in the preview.

Demo Mode:

For screen-recording demonstrations:

python snapguard.py --record

This keeps the preview visible to screen-recording software.

Technology Stack:

* Python — application logic
* MSS — screen capture
* RapidOCR / ONNX Runtime — on-device OCR
* OpenCV — image processing and pixelation
* Regex pattern matching — sensitive-data detection
* PyWin32 / Windows APIs — window handling and privacy controls

Current Prototype Limitations:

This is a working proof-of-concept rather than a production-ready screen-sharing system.

The current implementation uses CPU-based ONNX Runtime processing. Snapdragon NPU/QNN acceleration is planned as a future optimization.

The current prototype also outputs the protected feed through its preview window rather than a virtual camera.

OCR processing introduces some latency between a sensitive item appearing and its detection.

Future Development:

If developed further, SnapGuard can be extended with:

* Snapdragon NPU acceleration using Qualcomm QNN
* Virtual camera output for applications such as video conferencing
* More advanced AI-based sensitive-information detection
* Improved tracking between OCR frames
* Lower-latency processing
* More configurable privacy policies
* Application-specific protection rules
* Improved false-positive handling
* Performance optimization for Snapdragon platforms

Project Status

Working prototype

The current prototype demonstrates the core concept:

Capture → Detect → Protect → Preview

SnapGuard is designed as a foundation for a Snapdragon-optimized, privacy-preserving screen-sharing solution.
