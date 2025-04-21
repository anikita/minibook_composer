#!/usr/bin/env python3
"""
tts.py: Text-to-speech integration for Minibook Composer using Google Cloud Text-to-Speech API.
"""
import os
import sys
import base64
import logging
import argparse
import requests
from config import API_TTS_KEY, OUTPUT_FOLDER, PROJECT_FOLDER

# --- User Configurable Defaults (for IDE runs or no-arg calls) ---
DEFAULT_TEXT_INPUT = "Hello from the Minibook Composer TTS module!"
# To use a file by default, set DEFAULT_TEXT_INPUT = None and provide a path below
DEFAULT_INPUT_FILE = None  # e.g., "path/to/your/input.txt"
DEFAULT_OUTPUT_FILENAME = "default_tts_output.mp3"
DEFAULT_LANGUAGE_CODE = "en-US"
DEFAULT_VOICE_NAME = "en-US-Wavenet-D" # Find more voices: https://cloud.google.com/text-to-speech/docs/voices
DEFAULT_SPEAKING_RATE = 1.0
DEFAULT_PITCH = 0.0
DEFAULT_AUDIO_ENCODING = "MP3" # Options: MP3, LINEAR16, OGG_OPUS
# -------------------------------------------------------------------


def synthesize_text_to_file(
    text: str,
    filename: str,
    language_code: str = DEFAULT_LANGUAGE_CODE,
    voice_name: str = DEFAULT_VOICE_NAME,
    speaking_rate: float = DEFAULT_SPEAKING_RATE,
    pitch: float = DEFAULT_PITCH,
    audio_encoding: str = DEFAULT_AUDIO_ENCODING,
) -> str:
    """
    Synthesizes speech from the given text and saves it to a file under OUTPUT_FOLDER/PROJECT_FOLDER/audio.
    Returns the full path to the generated audio file.
    """
    # Prepare output directory
    # Ensure PROJECT_FOLDER exists within OUTPUT_FOLDER
    project_base_path = os.path.join(OUTPUT_FOLDER, PROJECT_FOLDER)
    os.makedirs(project_base_path, exist_ok=True)
    audio_dir = os.path.join(project_base_path, "audio")
    os.makedirs(audio_dir, exist_ok=True)
    output_path = os.path.join(audio_dir, filename)

    # Prepare REST request to Google TTS API
    if not API_TTS_KEY:
        raise ValueError("API_TTS_KEY is not set in config.py or environment variables.")

    url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={API_TTS_KEY}"
    payload = {
        "input": {"text": text},
        "voice": {"languageCode": language_code, "name": voice_name},
        "audioConfig": {
            "audioEncoding": audio_encoding,
            "speakingRate": speaking_rate,
            "pitch": pitch,
        },
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)
    except requests.exceptions.RequestException as e:
        logging.error(f"HTTP Request failed: {e}")
        # Optionally: Include more response details for debugging
        # logging.error(f"Response status: {response.status_code}, Response text: {response.text}")
        raise

    response_data = response.json()
    audio_content = response_data.get("audioContent")

    if not audio_content:
        logging.error(f"TTS API did not return audio content. Response: {response_data}")
        raise RuntimeError("No audioContent returned from TTS API")

    try:
        audio_bytes = base64.b64decode(audio_content)
    except (TypeError, base64.binascii.Error) as e:
        logging.error(f"Failed to decode base64 audio content: {e}")
        raise

    try:
        with open(output_path, "wb") as out_f:
            out_f.write(audio_bytes)
        logging.info(f"Audio content written to {output_path}")
        return output_path
    except IOError as e:
        logging.error(f"Failed to write audio file to {output_path}: {e}")
        raise


def main():
    parser = argparse.ArgumentParser(description="Minibook Composer Text-to-Speech CLI")
    input_group = parser.add_mutually_exclusive_group(required=False) # Not required if using defaults
    input_group.add_argument("--text", help="Text to synthesize into speech")
    input_group.add_argument("--input-file", help="Path to a text file to synthesize")

    parser.add_argument(
        "--output", default=DEFAULT_OUTPUT_FILENAME,
        help="Filename to save the synthesized audio (within project audio dir)"
    )
    parser.add_argument(
        "--language", default=DEFAULT_LANGUAGE_CODE, help="BCP-47 language code"
    )
    parser.add_argument(
        "--voice", default=DEFAULT_VOICE_NAME, help="Voice name (e.g., en-US-Wavenet-D)"
    )
    parser.add_argument(
        "--speaking_rate", type=float, default=DEFAULT_SPEAKING_RATE,
        help="Speaking rate (0.25–4.0)"
    )
    parser.add_argument(
        "--pitch", type=float, default=DEFAULT_PITCH,
        help="Pitch (-20.0–20.0)"
    )
    args = parser.parse_args()

    # Basic logging setup
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    # Determine parameters: Use CLI args if provided, otherwise use defaults
    text_to_synthesize = args.text
    input_file_path = args.input_file
    output_filename = args.output
    lang_code = args.language
    voice = args.voice
    rate = args.speaking_rate
    pitch_val = args.pitch

    # If no input specified via CLI, use defaults from the top of the file
    if not text_to_synthesize and not input_file_path:
        if DEFAULT_INPUT_FILE:
            input_file_path = DEFAULT_INPUT_FILE
            logging.info(f"No input CLI arg detected, using default file: {input_file_path}")
        elif DEFAULT_TEXT_INPUT:
            text_to_synthesize = DEFAULT_TEXT_INPUT
            logging.info("No input CLI arg detected, using default text.")
        else:
            logging.error("Error: No input text or file specified via CLI or defaults.")
            sys.exit(1) # Exit if no input source is determined

    # Read from file if specified (either by CLI or default)
    if input_file_path:
        try:
            with open(input_file_path, 'r', encoding='utf-8') as f:
                text_to_synthesize = f.read()
            logging.info(f"Read text from {input_file_path}")
        except FileNotFoundError:
            logging.error(f"Error: Input file not found: {input_file_path}")
            sys.exit(1)
        except Exception as e:
            logging.error(f"Error reading input file {input_file_path}: {e}")
            sys.exit(1)

    if not text_to_synthesize:
        logging.error("Error: No text available for synthesis after checking args and defaults.")
        sys.exit(1)

    try:
        synthesize_text_to_file(
            text=text_to_synthesize,
            filename=output_filename,
            language_code=lang_code,
            voice_name=voice,
            speaking_rate=rate,
            pitch=pitch_val,
            # Using the default audio encoding defined at the top
            audio_encoding=DEFAULT_AUDIO_ENCODING
        )
    except Exception as e:
         # More specific error logging might be helpful depending on expected errors
         logging.error(f"Error during text synthesis processing: {e}")
         # Consider re-raising or sys.exit(1) based on desired script behavior on failure
         sys.exit(1)


if __name__ == "__main__":
    main() 