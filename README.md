# Voice to Text Converter with OpenAI Whisper

A modern GUI application that converts audio files to text with high accuracy using OpenAI's Whisper model.

## Features

- **High Accuracy**: Uses OpenAI Whisper for state-of-the-art speech recognition
- **Multiple Model Sizes**: Choose from tiny, base, small, medium, or large models
- **User-Friendly GUI**: Clean tkinter interface with progress indicators
- **Multiple Audio Formats**: Supports MP3, WAV, M4A, FLAC, AAC, OGG, WMA
- **Auto Language Detection**: Automatically detects the language in audio
- **Export Options**: Copy to clipboard or save as text file
- **Threading**: Non-blocking processing to keep GUI responsive

## Installation

1. **Clone or download this project**

2. **Create and activate virtual environment** (recommended):
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # On Windows
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. **Run the application**:
   ```bash
   python voice_to_text_app.py
   ```

2. **Select Model Size**:
   - **tiny**: Fastest, least accurate (~39 MB)
   - **base**: Good balance of speed and accuracy (~74 MB) - Default
   - **small**: Better accuracy (~244 MB)
   - **medium**: High accuracy (~769 MB)
   - **large**: Best accuracy (~1550 MB)

3. **Select Audio File**:
   - Click "Select Audio File" button
   - Choose your audio file from the dialog

4. **Convert**:
   - Click "Convert to Text" button
   - Wait for processing (progress bar will show activity)
   - View transcribed text in the text area

5. **Export Results**:
   - **Copy Text**: Copy transcription to clipboard
   - **Save as TXT**: Save transcription to a text file
   - **Clear**: Clear the text area

## Supported Audio Formats

- MP3
- WAV
- M4A
- FLAC
- AAC
- OGG
- WMA

## Model Information

The application uses OpenAI Whisper models with the following characteristics:

| Model  | Size   | Accuracy | Speed |
|--------|--------|----------|-------|
| tiny   | ~39 MB | Good     | Fast  |
| base   | ~74 MB | Better   | Fast  |
| small  | ~244 MB| High     | Medium|
| medium | ~769 MB| Higher   | Slow  |
| large  | ~1550 MB| Highest | Slowest|

## Requirements

- Python 3.8+
- tkinter (usually included with Python)
- OpenAI Whisper
- PyTorch
- NumPy

## Notes

- First run will download the selected Whisper model
- Larger models provide better accuracy but require more time and memory
- The application automatically detects the language in the audio
- Processing time depends on audio length and model size

## Troubleshooting

- **Model loading fails**: Ensure you have sufficient disk space and internet connection
- **Audio file not supported**: Try converting to MP3 or WAV format
- **Out of memory**: Try using a smaller model size
- **Slow processing**: Use a smaller model or shorter audio files
