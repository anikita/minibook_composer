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
import re
import time
import json
from google.cloud import texttospeech
from google.cloud import storage
from config import API_TTS_KEY, OUTPUT_FOLDER, PROJECT_FOLDER, GCP_PROJECT_ID, GCP_BUCKET_NAME

# --- User Configurable Defaults (for IDE runs or no-arg calls) ---

# Example text that can be used by setting DEFAULT_TEXT_INPUT to this value
EXAMPLE_TEXT = """
Consider some common hurdles in science education:
• Abstract Nature: Many core scientific ideas deal with things we cannot directly see, hear, or touch – molecules, forces, energy fields, geological timescales, evolutionary processes spanning millions of years. Explaining cellular respiration without seeing mitochondria in action, or gravity without feeling the pull of massive objects across space, requires a leap of imagination that is difficult to achieve with mere definitions and diagrams.
   Counter-intuitive Phenomena: Some scientific realities defy our everyday experience. Quantum mechanics, the bending of spacetime by gravity, or the concept of inertia (an object in motion stays in motion unless acted upon) can feel fundamentally wrong* based on how we perceive the world.
• Information Overload: Science curricula are often packed with facts and terminology. Presenting these as isolated pieces of information can overwhelm students, leading to memorization without true understanding or the ability to connect ideas.
• Perceived Irrelevance: Students may struggle to see how learning about photosynthesis, chemical bonds, or planetary motion impacts their own lives or the world around them. Without a clear connection, the motivation to learn diminishes.
"""

# Google TTS API limits
STANDARD_TTS_CHAR_LIMIT = 5000  # Character limit for standard TTS API
LONG_TTS_CHAR_LIMIT = 100000  # Character limit for Long Audio API
USE_LONG_AUDIO_API = True  # Set to False to only use standard API
SKIP_EXISTING_AUDIO_FILES = True  # Set to False to reprocess files even if they already exist
LONG_AUDIO_TIMEOUT_SECONDS = 360  # Timeout in seconds for Long Audio API operations (5 minutes)
USE_SSML = True  # Use Speech Synthesis Markup Language for better speech control
FORCE_PLAIN_TEXT = True  # Force plain text mode even for SSML-compatible voices (until SSML issues are fixed)
SSML_RULES_FILE = "ssml_rules.json"  # File containing SSML transformation rules
MARKDOWN_RULES_FILE = "markdown_rules.json"  # File containing markdown preprocessing rules
DISABLE_SSL_VERIFICATION = False  # Set to True to disable SSL verification for testing
LONG_AUDIO_ENCODING = "LINEAR16"  # Only LINEAR16 is supported for Long Audio API

# List of voices known to support SSML
# https://cloud.google.com/text-to-speech/docs/ssml
SSML_COMPATIBLE_VOICES = [
    "en-US-Neural2-A", "en-US-Neural2-C", "en-US-Neural2-D", "en-US-Neural2-E", "en-US-Neural2-F", "en-US-Neural2-G", "en-US-Neural2-H", "en-US-Neural2-I", "en-US-Neural2-J",
    "en-US-Wavenet-A", "en-US-Wavenet-B", "en-US-Wavenet-C", "en-US-Wavenet-D", "en-US-Wavenet-E", "en-US-Wavenet-F", "en-US-Wavenet-G", "en-US-Wavenet-H", "en-US-Wavenet-I", "en-US-Wavenet-J",
    "en-US-Standard-A", "en-US-Standard-B", "en-US-Standard-C", "en-US-Standard-D", "en-US-Standard-E", "en-US-Standard-F", "en-US-Standard-G", "en-US-Standard-H", "en-US-Standard-I", "en-US-Standard-J",
    # Add more voices here as they become compatible
]
#WAV to MP3
AUTO_CONVERT_WAV_TO_MP3 = True  # Whether to automatically convert WAV files to MP3 when using Long Audio API
MP3_BITRATE = "64k"  # Default bitrate for MP3 conversion
AUDIO_SAMPLE_RATE = 22050  # Default audio sample rate in Hz (22050 is sufficient for speech)
AUDIO_BIT_DEPTH = 16  # Default bit depth (16-bit is standard for most audio)
AUDIO_CHANNELS = 1  # Default number of channels (1=mono, 2=stereo)

# Different input modes
# Inline text input mode, set DEFAULT_TEXT_INPUT to a string value
DEFAULT_TEXT_INPUT = None # Overriden if input file is specified
# Folder input  mode - has highest priority, looks in PROJECT_FOLDER
DEFAULT_INPUT_FOLDER = 'existentialism_in_the_digital_age_250427_1229' # e.g., "my_book" - will look for chapters/*.md files
# File input mode, set DEFAULT_TEXT_INPUT = None and provide a path below
DEFAULT_INPUT_FILE =  None #"./test_markdown.md"  # e.g., "path/to/your/input.txt"
DEFAULT_OUTPUT_FILENAME = None # "default_tts_output.mp3" # Overriden by the input file name if specified

#TTS Voice
DEFAULT_LANGUAGE_CODE = "en-US" #"el-GR", "en-US"
DEFAULT_VOICE_NAME = 'en-US-Chirp3-HD-Aoede' #'en-US-Chirp3-HD-Aoede', 'en-US-Neural2-C', 'en-US-Wavenet-D' # Find more voices: https://cloud.google.com/text-to-speech/docs/voices
DEFAULT_SPEAKING_RATE = 1.0
DEFAULT_PITCH = 0.0
DEFAULT_AUDIO_ENCODING = "MP3" # Options: MP3, LINEAR16, OGG_OPUS

# Enable this for testing when TTS API is not available
MOCK_MODE = False
# Whether to preprocess markdown by default
DEFAULT_PREPROCESS_MARKDOWN = True
# Whether to exclude tables from the text sent to TTS API
DEFAULT_EXCLUDE_TABLES = True
# Whether to save the processed text alongside the audio file
DEFAULT_SAVE_TEXT = True
# -------------------------------------------------------------------


def apply_ssml_rules(text):
    """
    Apply SSML (Speech Synthesis Markup Language) rules to the input text.
    This enhances the TTS output with better pauses, emphasis, and pronunciation.
    
    Parameters:
        text: Plain text to convert to SSML format
        
    Returns:
        Text with SSML tags applied
    """
    if not USE_SSML:
        return text
    
    # Create a simplified and safe version of the text for SSML
    # First, escape XML special characters
    ssml_text = text.replace("&", "&amp;")
    ssml_text = ssml_text.replace("<", "&lt;")
    ssml_text = ssml_text.replace(">", "&gt;")
    ssml_text = ssml_text.replace("\"", "&quot;")
    ssml_text = ssml_text.replace("'", "&apos;")
    
    # Load custom rules from file if it exists
    rules = []
    try:
        if os.path.exists(SSML_RULES_FILE):
            with open(SSML_RULES_FILE, 'r') as f:
                rules = json.load(f)
                logging.info(f"Loaded {len(rules)} SSML rules from {SSML_RULES_FILE}")
        else:
            logging.warning(f"SSML rules file {SSML_RULES_FILE} not found, using default rules")
    except Exception as e:
        logging.error(f"Error loading SSML rules: {e}")
    
    # Apply built-in rules and rules from file
    for rule in rules:
        try:
            # Skip disabled rules
            if rule.get("enabled") is False:
                logging.debug(f"Skipping disabled rule: {rule.get('description')}")
                continue
            
            # Apply rule based on type
            if rule.get("type") == "replace":
                pattern = rule.get("pattern")
                replacement = rule.get("replacement")
                if pattern and replacement:
                    ssml_text = ssml_text.replace(pattern, replacement)
                    logging.debug(f"Applied replace rule: {rule.get('description')}")
            elif rule.get("type") == "regex":
                pattern = rule.get("pattern")
                replacement = rule.get("replacement")
                if pattern and replacement:
                    try:
                        ssml_text = re.sub(pattern, replacement, ssml_text)
                        logging.debug(f"Applied regex rule: {rule.get('description')}")
                    except Exception as regex_error:
                        logging.error(f"Regex error applying rule {rule.get('description')}: {regex_error}")
        except Exception as e:
            logging.error(f"Error applying SSML rule {rule.get('description')}: {e}")
    
    # Finally, wrap the entire text in <speak> tags
    ssml_text = f"<speak>{ssml_text}</speak>"
    
    # Log the full SSML for debugging when in debug mode
    if logging.getLogger().getEffectiveLevel() <= logging.DEBUG:
        logging.debug(f"Full SSML:\n{ssml_text}")
    
    # Validate SSML
    try:
        import xml.etree.ElementTree as ET
        ET.fromstring(ssml_text)
        logging.debug("SSML validation passed")
    except Exception as xml_error:
        logging.error(f"Invalid SSML generated! XML parsing error: {xml_error}")
        # If SSML is invalid, fall back to plain text
        logging.warning("Falling back to plain text due to invalid SSML")
        return text
    
    # Log the length of the SSML 
    logging.info(f"Generated SSML of length {len(ssml_text)} characters")
    
    return ssml_text

def preprocess_text_for_tts(text, preprocess_md=True, exclude_tables=True, apply_ssml=USE_SSML, voice_name=DEFAULT_VOICE_NAME):
    """
    Prepare text for TTS by applying various preprocessing steps.
    
    Parameters:
        text: The original text
        preprocess_md: Whether to preprocess markdown
        exclude_tables: Whether to exclude tables
        apply_ssml: Whether to apply SSML rules
        voice_name: The voice to use (checks for SSML compatibility)
        
    Returns:
        Processed text ready for TTS
    """
    # First preprocess markdown if enabled
    if preprocess_md:
        processed_text = preprocess_markdown(text, exclude_tables=exclude_tables)
        
        # Log the processed text for debugging
        if logging.getLogger().getEffectiveLevel() <= logging.DEBUG:
            logging.debug(f"Text after markdown preprocessing:\n{processed_text[:500]}...")
    else:
        processed_text = text
        
    # Then apply SSML if enabled AND voice supports it AND force plain text is disabled
    if apply_ssml and voice_name in SSML_COMPATIBLE_VOICES and not FORCE_PLAIN_TEXT:
        processed_text = apply_ssml_rules(processed_text)
        logging.info(f"Applied SSML rules for compatible voice: {voice_name}")
    elif apply_ssml and voice_name not in SSML_COMPATIBLE_VOICES:
        logging.warning(f"Voice {voice_name} does not support SSML. Using plain text instead.")
    elif apply_ssml and FORCE_PLAIN_TEXT:
        logging.info("FORCE_PLAIN_TEXT is enabled. Using plain text mode despite SSML compatibility.")
        
    return processed_text

def preprocess_markdown(text, exclude_tables=DEFAULT_EXCLUDE_TABLES):
    """
    Preprocess markdown text to make it more suitable for text-to-speech.
    Removes or converts markdown syntax that would be read literally by TTS engines.
    
    Parameters:
        text: The markdown text to process
        exclude_tables: Whether to exclude tables from the output
    """
    # Try to load and apply rules from markdown_rules.json
    try:
        if os.path.exists(MARKDOWN_RULES_FILE):
            return preprocess_markdown_with_rules(text, exclude_tables)
        else:
            logging.warning(f"Markdown rules file {MARKDOWN_RULES_FILE} not found, using hardcoded rules")
            return preprocess_markdown_hardcoded(text, exclude_tables)
    except Exception as e:
        logging.error(f"Error in rule-based markdown preprocessing: {e}")
        logging.info("Falling back to hardcoded markdown preprocessing")
        return preprocess_markdown_hardcoded(text, exclude_tables)

def preprocess_markdown_hardcoded(text, exclude_tables=DEFAULT_EXCLUDE_TABLES):
    """
    Legacy hardcoded version of markdown preprocessing, used as fallback if rules file is not found.
    """
    # Remove heading markers
    text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
    
    # Remove bold/italic markers
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # Bold **text**
    text = re.sub(r'\*(.*?)\*', r'\1', text)      # Italic *text*
    text = re.sub(r'__(.*?)__', r'\1', text)      # Bold __text__
    text = re.sub(r'_(.*?)_', r'\1', text)        # Italic _text_
    
    # Handle links [text](url) -> just text
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
    
    # Remove code blocks and inline code
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)  # Code blocks
    text = re.sub(r'`(.*?)`', r'\1', text)  # Inline code
    
    # Exclude tables if enabled
    if exclude_tables:
        # Find and remove markdown tables
        # This regex looks for patterns like:
        # | header1 | header2 |
        # | ------- | ------- |
        # | data1   | data2   |
        
        # First, try to match standard markdown tables with separator row
        table_pattern = r'^\|.+\|$\n^\|[-:| ]+\|$(\n^\|.+\|$)*'
        text = re.sub(table_pattern, '\n[Table excluded from speech]\n', text, flags=re.MULTILINE)
        
        # Also try to match simpler tables without separator row (just consecutive rows with pipes)
        simple_table_pattern = r'(^\|.+\|$\n){2,}'
        text = re.sub(simple_table_pattern, '\n[Table excluded from speech]\n', text, flags=re.MULTILINE)
    
    # Handle bullet points
    text = re.sub(r'^\s*[-*+]\s+', '• ', text, flags=re.MULTILINE)  # Convert bullets to verbal pause
    
    # Handle numbered lists (keep the numbers)
    text = re.sub(r'^\s*(\d+)\.\s+', r'\1. ', text, flags=re.MULTILINE)
    
    # Handle horizontal rules
    text = re.sub(r'^\s*[-*_]{3,}\s*$', '\n', text, flags=re.MULTILINE)
    
    # Handle blockquotes
    text = re.sub(r'^\s*>\s+', '', text, flags=re.MULTILINE)
    
    # Add appropriate pauses for paragraph breaks (double newlines)
    text = re.sub(r'\n\s*\n', '\n\n', text)
    
    return text

def preprocess_markdown_with_rules(text, exclude_tables=DEFAULT_EXCLUDE_TABLES):
    """
    Preprocess markdown text using the rule-based approach from markdown_rules.json.
    """
    processed_text = text
    
    # Load markdown preprocessing rules from file
    rules = []
    try:
        with open(MARKDOWN_RULES_FILE, 'r') as f:
            rules = json.load(f)
            logging.info(f"Loaded {len(rules)} markdown rules from {MARKDOWN_RULES_FILE}")
    except Exception as e:
        logging.error(f"Error loading markdown rules: {e}")
        return preprocess_markdown_hardcoded(text, exclude_tables)
    
    # Apply rules from the configuration file
    for rule in rules:
        try:
            # Skip disabled rules
            if rule.get("enabled") is False:
                logging.debug(f"Skipping disabled markdown rule: {rule.get('description')}")
                continue
                
            # Skip table rules if exclude_tables is False
            if not exclude_tables and ("table" in rule.get("description", "").lower()):
                logging.debug(f"Skipping table rule because exclude_tables=False: {rule.get('description')}")
                continue
                
            if rule.get("type") == "regex":
                pattern = rule.get("pattern")
                replacement = rule.get("replacement")
                flags_str = rule.get("flags", "")
                
                if pattern and replacement is not None:
                    # Parse regex flags
                    flags = 0
                    if "IGNORECASE" in flags_str or "I" in flags_str:
                        flags |= re.IGNORECASE
                    if "MULTILINE" in flags_str or "M" in flags_str:
                        flags |= re.MULTILINE
                    if "DOTALL" in flags_str or "S" in flags_str:
                        flags |= re.DOTALL
                        
                    try:
                        # Compile the pattern first to ensure it's valid
                        compiled_pattern = re.compile(pattern, flags=flags)
                        # Use a function for replacement to properly handle capture groups
                        def replace_func(match):
                            result = replacement
                            # Handle capture groups ($1, $2, etc.)
                            for i in range(1, len(match.groups()) + 1):
                                placeholder = f"${i}"
                                if placeholder in result:
                                    result = result.replace(placeholder, match.group(i) or '')
                            return result
                        
                        processed_text = compiled_pattern.sub(replace_func, processed_text)
                        logging.debug(f"Applied markdown rule: {rule.get('description')}")
                    except Exception as regex_error:
                        logging.error(f"Regex error applying markdown rule {rule.get('description')}: {regex_error}")
            
            elif rule.get("type") == "replace":
                pattern = rule.get("pattern")
                replacement = rule.get("replacement")
                
                if pattern and replacement is not None:
                    processed_text = processed_text.replace(pattern, replacement)
                    logging.debug(f"Applied markdown replace rule: {rule.get('description')}")
                    
        except Exception as e:
            logging.error(f"Error applying markdown rule {rule.get('description')}: {e}")
    
    return processed_text


def synthesize_with_long_audio_api(
    text: str,
    output_filename: str,
    output_dir: str,
    language_code: str = DEFAULT_LANGUAGE_CODE,
    voice_name: str = DEFAULT_VOICE_NAME,
    speaking_rate: float = DEFAULT_SPEAKING_RATE,
    pitch: float = DEFAULT_PITCH,
    audio_encoding: str = DEFAULT_AUDIO_ENCODING,  # This is ignored for Long Audio API
) -> str:
    """
    Synthesizes long text using Google's Long Audio API.
    Returns the path to the downloaded audio file.
    
    Note: Requires GCP credentials setup and permissions to:
    - texttospeech.longAudioSynthesize API
    - Cloud Storage bucket access
    
    Note: Long Audio API only supports LINEAR16 format, regardless of audio_encoding parameter
    """
    # Import os at the function level to avoid scope issues
    import os
    
    try:
        # Print environment info for debugging
        logging.info(f"GCP_PROJECT_ID: {GCP_PROJECT_ID}")
        logging.info(f"GCP_BUCKET_NAME: {GCP_BUCKET_NAME}")
        
        if DISABLE_SSL_VERIFICATION:
            os.environ['GRPC_SSL_CIPHER_SUITES'] = 'HIGH+ECDSA'
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        # Create the texttospeech client
        try:
            client = texttospeech.TextToSpeechLongAudioSynthesizeClient()
            logging.info("Created TextToSpeechLongAudioSynthesizeClient successfully")
        except Exception as e:
            logging.error(f"Error creating TextToSpeechLongAudioSynthesizeClient: {e}")
            # Try alternative client creation
            from google.cloud.texttospeech import TextToSpeechClient
            client = TextToSpeechClient()
            logging.info("Falling back to standard TextToSpeechClient")
        
        # Configure storage client for output
        storage_client = storage.Client()
        
        # Configure the voice request
        voice = texttospeech.VoiceSelectionParams(
            language_code=language_code,
            name=voice_name
        )
        
        # Long Audio API only supports LINEAR16 encoding
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16,
            speaking_rate=speaking_rate,
            pitch=pitch,
        )
        
        # Adjust output filename to have .wav extension since we use LINEAR16
        output_filename_base = os.path.splitext(output_filename)[0]
        output_filename_wav = f"{output_filename_base}.wav"
        
        # Create unique output path in GCS bucket
        timestamp = int(time.time())
        gcs_output_path = f"gs://{GCP_BUCKET_NAME}/tts_output_{timestamp}/{output_filename_wav}"
        logging.info(f"Long Audio API output path: {gcs_output_path}")
        
        # Set the input based on whether text contains SSML tags
        is_ssml = text.startswith("<speak>") and text.endswith("</speak>")
        if is_ssml:
            input_text = texttospeech.SynthesisInput(ssml=text)
            logging.info("Using SSML input for Long Audio API")
        else:
            input_text = texttospeech.SynthesisInput(text=text)
            logging.info("Using plain text input for Long Audio API")
        
        # Create the request
        parent = f"projects/{GCP_PROJECT_ID}/locations/global"
        
        # Call the Long Audio API using the proper request format
        request = texttospeech.SynthesizeLongAudioRequest(
            parent=parent,
            input=input_text,
            voice=voice,
            audio_config=audio_config,
            output_gcs_uri=gcs_output_path
        )
        
        logging.info("Starting Long Audio synthesis with proper request format")
        operation = client.synthesize_long_audio(request=request)
        
        logging.info("Long Audio synthesis started, this may take several minutes...")
        
        # Wait for the operation to complete
        response = operation.result(timeout=LONG_AUDIO_TIMEOUT_SECONDS)  # Using the configurable timeout
        logging.info(f"Long Audio synthesis complete: {response}")
        
        # Download the result from GCS
        bucket = storage_client.bucket(GCP_BUCKET_NAME)
        # Extract the object name from gcs_output_path (remove 'gs://bucket_name/' part)
        object_name = gcs_output_path.replace(f"gs://{GCP_BUCKET_NAME}/", "")
        blob = bucket.blob(object_name)
        
        # Create local output path
        local_output_path = os.path.join(output_dir, output_filename_wav)
        
        # Download the file to the specified path
        blob.download_to_filename(local_output_path)
        logging.info(f"Audio downloaded to: {local_output_path}")
        
        # If original request was for MP3, convert the WAV to MP3
        if audio_encoding.upper() == "MP3" and AUTO_CONVERT_WAV_TO_MP3:
            try:
                from pydub import AudioSegment
                mp3_path = os.path.join(output_dir, output_filename)
                
                # Load the WAV file
                audio = AudioSegment.from_wav(local_output_path)
                
                # Apply audio parameters
                audio = audio.set_frame_rate(AUDIO_SAMPLE_RATE)
                audio = audio.set_sample_width(AUDIO_BIT_DEPTH // 8)  # Convert bits to bytes
                audio = audio.set_channels(AUDIO_CHANNELS)
                
                # Export with the specified parameters
                audio.export(
                    mp3_path, 
                    format="mp3", 
                    bitrate=MP3_BITRATE,
                    parameters=["-q:a", "0"]  # Use highest quality encoding
                )
                
                logging.info(f"Converted WAV to MP3: {mp3_path} (bitrate: {MP3_BITRATE}, "
                             f"sample rate: {AUDIO_SAMPLE_RATE} Hz, bit depth: {AUDIO_BIT_DEPTH}-bit, "
                             f"channels: {AUDIO_CHANNELS})")
                
                # Remove the WAV file to save space
                os.remove(local_output_path)
                
                # Return the MP3 path
                return mp3_path
            except Exception as e:
                logging.error(f"Failed to convert WAV to MP3: {e}")
                logging.info("Keeping WAV format")
        
        return local_output_path
        
    except Exception as e:
        logging.error(f"Error in Long Audio API synthesis: {e}")
        raise


def get_safe_text_length(text, limit=STANDARD_TTS_CHAR_LIMIT):
    """
    Calculate a safe text length that's guaranteed to be under the byte limit.
    We need to account for the fact that some characters might be multi-byte.
    
    Parameters:
        text: The text to truncate
        limit: The maximum byte limit
        
    Returns:
        The safe length in characters to truncate to
    """
    # Start with a conservative estimate - UTF-8 can use up to 4 bytes per character
    safe_char_limit = limit // 4  
    
    # Binary search to find the optimal safe length
    min_len = 0
    max_len = min(len(text), limit)
    
    while min_len <= max_len:
        mid = (min_len + max_len) // 2
        if len(text[:mid].encode('utf-8')) <= limit:
            min_len = mid + 1
        else:
            max_len = mid - 1
    
    # max_len is now the largest length that stays under the byte limit
    return max_len


def synthesize_text_to_file(
    text: str,
    filename: str,
    language_code: str = DEFAULT_LANGUAGE_CODE,
    voice_name: str = DEFAULT_VOICE_NAME,
    speaking_rate: float = DEFAULT_SPEAKING_RATE,
    pitch: float = DEFAULT_PITCH,
    audio_encoding: str = DEFAULT_AUDIO_ENCODING,
    preprocess_md: bool = DEFAULT_PREPROCESS_MARKDOWN,
    exclude_tables: bool = DEFAULT_EXCLUDE_TABLES,
    save_text: bool = DEFAULT_SAVE_TEXT,
    input_file_path: str = None,
) -> str:
    """
    Synthesizes speech from the given text and saves it to a file under PROJECT_FOLDER/audio/project_name/audio.
    Returns the full path to the generated audio file.
    
    Parameters:
        text: The text to synthesize
        filename: The output filename
        language_code: BCP-47 language code
        voice_name: Voice name to use
        speaking_rate: Speed of speech (0.25-4.0)
        pitch: Voice pitch (-20.0-20.0)
        audio_encoding: Audio format (MP3, LINEAR16, OGG_OPUS)
        preprocess_md: Whether to preprocess Markdown syntax
        exclude_tables: Whether to exclude tables from the text sent to the TTS API
        save_text: Whether to save the processed text alongside the audio file
        input_file_path: Path to the input file (used to determine project folder name)
    """
    # Check if voice supports SSML
    use_ssml = USE_SSML and voice_name in SSML_COMPATIBLE_VOICES and not FORCE_PLAIN_TEXT
    if USE_SSML and voice_name not in SSML_COMPATIBLE_VOICES:
        logging.warning(f"Voice {voice_name} does not support SSML. Using plain text instead.")
    elif USE_SSML and FORCE_PLAIN_TEXT:
        logging.info("FORCE_PLAIN_TEXT is enabled. Using plain text mode despite SSML compatibility.")
    
    # Preprocess text for TTS (markdown and SSML if supported)
    processed_text = preprocess_text_for_tts(
        text, 
        preprocess_md=preprocess_md, 
        exclude_tables=exclude_tables,
        apply_ssml=use_ssml,
        voice_name=voice_name
    )
    
    # Determine project folder name based on input source
    if input_file_path:
        # Extract the base name without extension from the input file path
        project_name = os.path.splitext(os.path.basename(input_file_path))[0]
        logging.info(f"Creating project folder named after input file: {project_name}")
    else:
        # Using DEFAULT_TEXT_INPUT
        project_name = "DEFAULT_TEXT_INPUT"
        logging.info("Creating DEFAULT_TEXT_INPUT project folder")
    
    # Create the project directory structure
    # First ensure the main audio folder exists
    audio_base_folder = os.path.join(PROJECT_FOLDER, "audio")
    os.makedirs(audio_base_folder, exist_ok=True)
    
    # Then create the project-specific folder within audio
    base_path = os.path.join(audio_base_folder, project_name)
    logging.info(f"Output base path: {base_path}")
    os.makedirs(base_path, exist_ok=True)
    
    # Create audio and text subdirectories within the project folder
    audio_dir = os.path.join(base_path, "audio")
    text_dir = os.path.join(base_path, "text")
    os.makedirs(audio_dir, exist_ok=True)
    os.makedirs(text_dir, exist_ok=True)
    
    # Save the processed text if requested
    if save_text and not MOCK_MODE:
        text_filename = os.path.splitext(filename)[0] + ".txt"
        text_path = os.path.join(text_dir, text_filename)
        try:
            with open(text_path, "w", encoding="utf-8") as f:
                if preprocess_md:
                    f.write("# Original Text\n\n")
                    f.write(text)
                    f.write("\n\n# Processed Text (sent to TTS API)\n\n")
                    f.write(processed_text)
                else:
                    f.write(processed_text)
            logging.info(f"Text content saved to {text_path}")
        except IOError as e:
            logging.error(f"Failed to write text file to {text_path}: {e}")
            # Continue with audio generation even if text saving fails
    
    # If we're in mock mode, just create a text file with the content
    if MOCK_MODE:
        # Change extension to .txt for mock mode
        mock_filename = os.path.splitext(filename)[0] + ".txt"
        output_path = os.path.join(audio_dir, mock_filename)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"MOCK TTS OUTPUT\n\n")
            f.write(f"Language: {language_code}\n")
            f.write(f"Voice: {voice_name}\n")
            f.write(f"Speaking Rate: {speaking_rate}\n")
            f.write(f"Pitch: {pitch}\n")
            f.write(f"Audio Encoding: {audio_encoding}\n")
            f.write(f"Markdown Preprocessing: {preprocess_md}\n")
            f.write(f"Table Exclusion: {exclude_tables}\n\n")
            
            if preprocess_md:
                f.write(f"Original Text:\n{text}\n\n")
                f.write(f"Processed Text (Markdown removed):\n{processed_text}")
            else:
                f.write(f"Text content (no preprocessing):\n{text}")
        logging.info(f"Mock mode enabled. Text content written to {output_path}")
        return output_path
        
    output_path = os.path.join(audio_dir, filename)

    # Prepare REST request to Google TTS API
    if not API_TTS_KEY:
        raise ValueError("API_TTS_KEY is not set in config.py or environment variables.")

    url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={API_TTS_KEY}"
    
    # Check if the processed text has SSML tags
    is_ssml = processed_text.startswith("<speak>") and processed_text.endswith("</speak>")
    
    # Configure the input type based on whether SSML is used
    if is_ssml:
        input_data = {"ssml": processed_text}
        logging.info("Using SSML input for speech synthesis")
    else:
        input_data = {"text": processed_text}
        logging.info("Using plain text input for speech synthesis")
    
    payload = {
        "input": input_data,
        "voice": {"languageCode": language_code, "name": voice_name},
        "audioConfig": {
            "audioEncoding": audio_encoding,
            "speakingRate": speaking_rate,
            "pitch": pitch,
        },
    }
    
    # Log the first part of the payload for debugging
    safe_payload = payload.copy()
    if "input" in safe_payload and "ssml" in safe_payload["input"]:
        ssml_content = safe_payload["input"]["ssml"]
        safe_payload["input"]["ssml"] = ssml_content[:100] + "..." if len(ssml_content) > 100 else ssml_content
    logging.info(f"API Request payload: {safe_payload}")
    
    try:
        response = requests.post(url, json=payload)
        if response.status_code != 200:
            logging.error(f"API Error: {response.status_code} {response.reason}")
            try:
                error_details = response.json()
                logging.error(f"API Error details: {error_details}")
            except:
                logging.error(f"Raw response: {response.text[:500]}")
        response.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            logging.error(f"HTTP Request failed: {e}")
            logging.error("API access is forbidden. This could be due to:")
            logging.error("1. The API key is invalid or expired")
            logging.error("2. The API key doesn't have access to the Text-to-Speech API")
            logging.error("3. The Text-to-Speech API is not enabled for this project")
            logging.error("\nTo fix this:")
            logging.error("- Enable the Text-to-Speech API for your project at: https://console.cloud.google.com/apis/library/texttospeech.googleapis.com")
            logging.error("- Verify your API key has the correct permissions")
            logging.error("- Check if you've exceeded your quota or if billing is enabled")
        elif e.response.status_code == 400:
            logging.error(f"Bad Request (400) error: {e}")
            try:
                error_details = e.response.json()
                logging.error(f"API Error details: {error_details}")
            except:
                pass
            logging.error("Possible causes for 400 errors:")
            logging.error("1. Text contains invalid characters")
            logging.error("2. Text is too long (try breaking it into smaller chunks)")
            logging.error("3. Invalid voice name or language code")
        else:
            logging.error(f"HTTP Request failed: {e}")
        
        # Create a small MP3 with error message for user awareness
        logging.info("Creating error placeholder audio file")
        try:
            # Write a minimal mp3 file that indicates an error
            error_url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={API_TTS_KEY}"
            error_payload = {
                "input": {"text": "There was an error processing this text with the Text to Speech API."},
                "voice": {"languageCode": language_code, "name": voice_name},
                "audioConfig": {
                    "audioEncoding": audio_encoding,
                    "speakingRate": speaking_rate,
                    "pitch": pitch,
                },
            }
            
            error_response = requests.post(error_url, json=error_payload)
            if error_response.status_code == 200:
                error_data = error_response.json()
                error_audio = error_data.get("audioContent")
                if error_audio:
                    error_bytes = base64.b64decode(error_audio)
                    with open(output_path, "wb") as out_f:
                        out_f.write(error_bytes)
                    logging.info(f"Created error audio placeholder: {output_path}")
                    return output_path
        except:
            logging.error("Failed to create error audio placeholder")
            
        # If all else fails, create an empty file so there's at least something
        try:
            with open(output_path, "wb") as out_f:
                out_f.write(b"")
            logging.warning(f"Created empty file due to API error: {output_path}")
            return output_path
        except:
            pass
            
        raise
    except requests.exceptions.RequestException as e:
        logging.error(f"HTTP Request failed: {e}")
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


def process_folder_input(folder_name):
    """
    Process all markdown files in the PROJECT_FOLDER/folder_name/chapters directory.
    
    Parameters:
        folder_name: The name of the input folder
    
    Returns:
        True if at least one file was processed, False otherwise
    """
    # Construct the path to the chapters folder - try both with and without PROJECT_FOLDER
    # First try with PROJECT_FOLDER (the standard case)
    chapters_path = os.path.join(PROJECT_FOLDER, folder_name, "chapters")
    logging.info(f"Looking for markdown files in: {chapters_path}")
    
    # If that doesn't exist, try without PROJECT_FOLDER (in case folder_name is already a full path)
    if not os.path.exists(chapters_path):
        alternate_path = os.path.join(folder_name, "chapters")
        logging.info(f"First path not found, trying alternate path: {alternate_path}")
        
        if os.path.exists(alternate_path):
            chapters_path = alternate_path
        else:
            # One more attempt, try directly from current directory
            current_dir_path = os.path.join(os.getcwd(), folder_name, "chapters")
            logging.info(f"Second path not found, trying from current directory: {current_dir_path}")
            
            if os.path.exists(current_dir_path):
                chapters_path = current_dir_path
    
    # Check if the chapters folder exists
    if not os.path.exists(chapters_path):
        logging.error(f"Chapters folder not found after all attempts")
        return False
    
    logging.info(f"Found chapters folder at: {chapters_path}")
    
    # Get all markdown files in the chapters folder
    try:
        markdown_files = [f for f in os.listdir(chapters_path) if f.endswith('.md')]
    except Exception as e:
        logging.error(f"Error accessing chapters folder: {e}")
        return False
    
    if not markdown_files:
        logging.error(f"No markdown files found in {chapters_path}")
        return False
    
    logging.info(f"Found {len(markdown_files)} markdown files to process in {chapters_path}")
    
    # Create output directories - use the same base path as found for input
    folder_base_path = os.path.dirname(chapters_path)
    audio_output_dir = os.path.join(folder_base_path, "audio")
    logging.info(f"Creating audio output directory: {audio_output_dir}")
    os.makedirs(audio_output_dir, exist_ok=True)
    
    if DEFAULT_SAVE_TEXT:
        text_output_dir = os.path.join(folder_base_path, "text")
        logging.info(f"Creating text output directory: {text_output_dir}")
        os.makedirs(text_output_dir, exist_ok=True)
    
    # Process each file
    success_count = 0
    skip_count = 0
    for md_file in markdown_files:
        file_path = os.path.join(chapters_path, md_file)
        base_name = os.path.splitext(md_file)[0]
        output_file = f"{base_name}.{DEFAULT_AUDIO_ENCODING.lower()}"
        output_path = os.path.join(audio_output_dir, output_file)
        
        # Check if file already exists and should be skipped
        if SKIP_EXISTING_AUDIO_FILES and os.path.exists(output_path):
            logging.info(f"Skipping {md_file} as output file already exists: {output_path}")
            skip_count += 1
            continue
        
        logging.info(f"Processing file: {file_path}")
        
        try:
            # Read the markdown file
            with open(file_path, 'r', encoding='utf-8') as f:
                text_content = f.read()
            
            # Process the text through TTS
            output_path = synthesize_text_to_folder(
                text=text_content,
                filename=output_file,
                folder_name=folder_name,
                preprocess_md=DEFAULT_PREPROCESS_MARKDOWN,
                exclude_tables=DEFAULT_EXCLUDE_TABLES,
                save_text=DEFAULT_SAVE_TEXT,
                folder_base_path=folder_base_path
            )
            
            logging.info(f"Created audio file: {output_path}")
            success_count += 1
            
        except Exception as e:
            logging.error(f"Error processing file {file_path}: {e}")
            continue
    
    if skip_count > 0:
        logging.info(f"Skipped {skip_count} files that already exist")
        
    if success_count > 0:
        logging.info(f"Successfully processed {success_count} of {len(markdown_files) - skip_count} files")
        return True
    elif skip_count > 0:
        logging.info(f"No new files processed, but {skip_count} existing files were skipped")
        return True
    else:
        logging.error("Failed to process any files")
        return False

def synthesize_text_to_folder(
    text: str,
    filename: str,
    folder_name: str,
    language_code: str = DEFAULT_LANGUAGE_CODE,
    voice_name: str = DEFAULT_VOICE_NAME,
    speaking_rate: float = DEFAULT_SPEAKING_RATE,
    pitch: float = DEFAULT_PITCH,
    audio_encoding: str = DEFAULT_AUDIO_ENCODING,
    preprocess_md: bool = DEFAULT_PREPROCESS_MARKDOWN,
    exclude_tables: bool = DEFAULT_EXCLUDE_TABLES,
    save_text: bool = DEFAULT_SAVE_TEXT,
    folder_base_path: str = None,
) -> str:
    """
    Synthesizes speech from the given text and saves it directly to the folder structure.
    This is a simpler version used by the folder input mode.
    
    Parameters:
        text: The text to synthesize
        filename: The output filename
        folder_name: The project folder name
        language_code: BCP-47 language code
        voice_name: Voice name to use
        speaking_rate: Speed of speech (0.25-4.0)
        pitch: Voice pitch (-20.0-20.0)
        audio_encoding: Audio format (MP3, LINEAR16, OGG_OPUS)
        preprocess_md: Whether to preprocess Markdown syntax
        exclude_tables: Whether to exclude tables from the text sent to the TTS API
        save_text: Whether to save the processed text alongside the audio file
        folder_base_path: Base path for the folder (if None, will use PROJECT_FOLDER/folder_name)
    """
    # Define output paths
    if folder_base_path:
        audio_dir = os.path.join(folder_base_path, "audio")
        if save_text:
            text_dir = os.path.join(folder_base_path, "text")
    else:
        # Fallback to original behavior
        audio_dir = os.path.join(PROJECT_FOLDER, folder_name, "audio")
        if save_text:
            text_dir = os.path.join(PROJECT_FOLDER, folder_name, "text")
    
    # Check if output file already exists
    output_path = os.path.join(audio_dir, filename)
    if SKIP_EXISTING_AUDIO_FILES and os.path.exists(output_path):
        logging.info(f"Output file already exists, skipping: {output_path}")
        return output_path
    
    # Check if voice supports SSML
    use_ssml = USE_SSML and voice_name in SSML_COMPATIBLE_VOICES and not FORCE_PLAIN_TEXT
    if USE_SSML and voice_name not in SSML_COMPATIBLE_VOICES:
        logging.warning(f"Voice {voice_name} does not support SSML. Using plain text instead.")
    elif USE_SSML and FORCE_PLAIN_TEXT:
        logging.info("FORCE_PLAIN_TEXT is enabled. Using plain text mode despite SSML compatibility.")
    
    # Preprocess text for TTS (markdown and SSML if supported)
    processed_text = preprocess_text_for_tts(
        text, 
        preprocess_md=preprocess_md, 
        exclude_tables=exclude_tables,
        apply_ssml=use_ssml,
        voice_name=voice_name
    )
    
    # Save the processed text if requested
    if save_text and not MOCK_MODE:
        text_filename = os.path.splitext(filename)[0] + ".txt"
        text_path = os.path.join(text_dir, text_filename)
        try:
            with open(text_path, "w", encoding="utf-8") as f:
                if preprocess_md:
                    f.write("# Original Text\n\n")
                    f.write(text)
                    f.write("\n\n# Processed Text (sent to TTS API)\n\n")
                    f.write(processed_text)
                else:
                    f.write(processed_text)
            logging.info(f"Text content saved to {text_path}")
        except IOError as e:
            logging.error(f"Failed to write text file to {text_path}: {e}")
    
    # If we're in mock mode, just create a text file with the content
    if MOCK_MODE:
        # Change extension to .txt for mock mode
        mock_filename = os.path.splitext(filename)[0] + ".txt"
        output_path = os.path.join(audio_dir, mock_filename)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"MOCK TTS OUTPUT\n\n")
            f.write(f"Language: {language_code}\n")
            f.write(f"Voice: {voice_name}\n")
            f.write(f"Speaking Rate: {speaking_rate}\n")
            f.write(f"Pitch: {pitch}\n")
            f.write(f"Audio Encoding: {audio_encoding}\n")
            f.write(f"Markdown Preprocessing: {preprocess_md}\n")
            f.write(f"Table Exclusion: {exclude_tables}\n\n")
            
            if preprocess_md:
                f.write(f"Original Text:\n{text}\n\n")
                f.write(f"Processed Text (Markdown removed):\n{processed_text}")
            else:
                f.write(f"Text content (no preprocessing):\n{text}")
        logging.info(f"Mock mode enabled. Text content written to {output_path}")
        return output_path
    
    output_path = os.path.join(audio_dir, filename)
    
    # Check text length and decide which API to use
    text_length = len(processed_text)
    
    # Use Long Audio API for longer texts if enabled
    if text_length > STANDARD_TTS_CHAR_LIMIT and text_length <= LONG_TTS_CHAR_LIMIT and USE_LONG_AUDIO_API:
        logging.info(f"Text length ({text_length} chars) exceeds standard API limit. Using Long Audio API.")
        
        # Check if the required GCP configs are available
        if not GCP_PROJECT_ID or GCP_PROJECT_ID == 'YOUR_GCP_PROJECT_ID' or not GCP_BUCKET_NAME or GCP_BUCKET_NAME == 'YOUR_GCP_BUCKET_NAME':
            logging.warning("GCP project ID or bucket name not configured properly. Falling back to standard API with truncated text.")
            safe_length = get_safe_text_length(processed_text)
            processed_text = processed_text[:safe_length]
            logging.warning(f"Text truncated to {safe_length} characters for standard API")
        else:
            try:
                return synthesize_with_long_audio_api(
                    text=processed_text,
                    output_filename=filename,
                    output_dir=audio_dir,
                    language_code=language_code,
                    voice_name=voice_name,
                    speaking_rate=speaking_rate,
                    pitch=pitch,
                    audio_encoding=audio_encoding,
                )
            except Exception as e:
                logging.error(f"Long Audio API failed: {e}")
                # Create error placeholder file instead of falling back to standard API
                try:
                    error_filename = f"error_{filename}"
                    error_path = os.path.join(audio_dir, error_filename)
                    with open(error_path, "w", encoding="utf-8") as f:
                        f.write(f"Long Audio API failed: {e}")
                    logging.warning(f"Created error file at: {error_path}")
                except Exception as write_error:
                    logging.error(f"Failed to create error file: {write_error}")
                # Raise the original exception instead of falling back
                raise
    
    # Check if text is too long even for Long Audio API
    if text_length > LONG_TTS_CHAR_LIMIT:
        logging.warning(f"Text is too long ({text_length} chars) even for Long Audio API. Creating placeholder.")
        # Create a placeholder mp3 file
        try:
            # Write a minimal mp3 file that indicates the error
            url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={API_TTS_KEY}"
            placeholder_payload = {
                "input": {"text": "This text was too long to process with the Text to Speech API."},
                "voice": {"languageCode": language_code, "name": voice_name},
                "audioConfig": {
                    "audioEncoding": audio_encoding,
                    "speakingRate": speaking_rate,
                    "pitch": pitch,
                },
            }
            
            response = requests.post(url, json=placeholder_payload)
            if response.status_code == 200:
                response_data = response.json()
                audio_content = response_data.get("audioContent")
                if audio_content:
                    audio_bytes = base64.b64decode(audio_content)
                    with open(output_path, "wb") as out_f:
                        out_f.write(audio_bytes)
                    logging.info(f"Created placeholder audio for too-long text: {output_path}")
                    return output_path
            
            # If the above fails, create an empty file
            with open(output_path, "wb") as out_f:
                out_f.write(b"")
            logging.warning(f"Created empty placeholder file for too-long text: {output_path}")
            return output_path
            
        except Exception as e:
            logging.error(f"Failed to create placeholder for too-long text: {e}")
            raise
    
    # If text length is appropriate for standard API, use it
    # Do one final check to make sure we're under the byte limit
    if len(processed_text.encode('utf-8')) > 5000:
        safe_length = get_safe_text_length(processed_text)
        processed_text = processed_text[:safe_length]
        logging.warning(f"Text truncated to {safe_length} characters to stay under byte limit")
        
    logging.info(f"Using standard TTS API for {len(processed_text)} characters ({len(processed_text.encode('utf-8'))} bytes)")
    url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={API_TTS_KEY}"
    
    # Check if the processed text has SSML tags
    is_ssml = processed_text.startswith("<speak>") and processed_text.endswith("</speak>")
    
    # Configure the input type based on whether SSML is used
    if is_ssml:
        input_data = {"ssml": processed_text}
        logging.info("Using SSML input for speech synthesis")
    else:
        input_data = {"text": processed_text}
        logging.info("Using plain text input for speech synthesis")
        
    payload = {
        "input": input_data,
        "voice": {"languageCode": language_code, "name": voice_name},
        "audioConfig": {
            "audioEncoding": audio_encoding,
            "speakingRate": speaking_rate,
            "pitch": pitch,
        },
    }
    
    # Log the first part of the payload for debugging
    safe_payload = payload.copy()
    if "input" in safe_payload and "ssml" in safe_payload["input"]:
        ssml_content = safe_payload["input"]["ssml"]
        safe_payload["input"]["ssml"] = ssml_content[:100] + "..." if len(ssml_content) > 100 else ssml_content
    logging.info(f"API Request payload: {safe_payload}")
    
    try:
        response = requests.post(url, json=payload)
        if response.status_code != 200:
            logging.error(f"API Error: {response.status_code} {response.reason}")
            try:
                error_details = response.json()
                logging.error(f"API Error details: {error_details}")
            except:
                logging.error(f"Raw response: {response.text[:500]}")
        response.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            logging.error(f"HTTP Request failed: {e}")
            logging.error("API access is forbidden. This could be due to:")
            logging.error("1. The API key is invalid or expired")
            logging.error("2. The API key doesn't have access to the Text-to-Speech API")
            logging.error("3. The Text-to-Speech API is not enabled for this project")
            logging.error("\nTo fix this:")
            logging.error("- Enable the Text-to-Speech API for your project at: https://console.cloud.google.com/apis/library/texttospeech.googleapis.com")
            logging.error("- Verify your API key has the correct permissions")
            logging.error("- Check if you've exceeded your quota or if billing is enabled")
        elif e.response.status_code == 400:
            logging.error(f"Bad Request (400) error: {e}")
            try:
                error_details = e.response.json()
                logging.error(f"API Error details: {error_details}")
            except:
                pass
            logging.error("Possible causes for 400 errors:")
            logging.error("1. Text contains invalid characters")
            logging.error("2. Text is too long (try breaking it into smaller chunks)")
            logging.error("3. Invalid voice name or language code")
        else:
            logging.error(f"HTTP Request failed: {e}")
        
        # Create a small MP3 with error message for user awareness
        logging.info("Creating error placeholder audio file")
        try:
            # Write a minimal mp3 file that indicates an error
            error_url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={API_TTS_KEY}"
            error_payload = {
                "input": {"text": "There was an error processing this text with the Text to Speech API."},
                "voice": {"languageCode": language_code, "name": voice_name},
                "audioConfig": {
                    "audioEncoding": audio_encoding,
                    "speakingRate": speaking_rate,
                    "pitch": pitch,
                },
            }
            
            error_response = requests.post(error_url, json=error_payload)
            if error_response.status_code == 200:
                error_data = error_response.json()
                error_audio = error_data.get("audioContent")
                if error_audio:
                    error_bytes = base64.b64decode(error_audio)
                    with open(output_path, "wb") as out_f:
                        out_f.write(error_bytes)
                    logging.info(f"Created error audio placeholder: {output_path}")
                    return output_path
        except:
            logging.error("Failed to create error audio placeholder")
            
        # If all else fails, create an empty file so there's at least something
        try:
            with open(output_path, "wb") as out_f:
                out_f.write(b"")
            logging.warning(f"Created empty file due to API error: {output_path}")
            return output_path
        except:
            pass
            
        raise
    except requests.exceptions.RequestException as e:
        logging.error(f"HTTP Request failed: {e}")
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
    input_group.add_argument("--input-folder", help="Process all markdown files in the specified folder's chapters directory")

    parser.add_argument(
        "--output", help="Filename to save the synthesized audio (within project audio dir)"
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
    parser.add_argument(
        "--no-markdown", action="store_true", 
        help="Disable markdown preprocessing (for plain text input)"
    )
    parser.add_argument(
        "--include-tables", action="store_true",
        help="Include tables in the text sent to TTS API (by default tables are excluded)"
    )
    parser.add_argument(
        "--mock", action="store_true",
        help="Use mock mode (creates a text file instead of audio)"
    )
    parser.add_argument(
        "--no-save-text", action="store_true",
        help="Don't save the processed text alongside the audio file"
    )
    parser.add_argument(
        "--no-convert-wav-to-mp3", action="store_true",
        help="Don't automatically convert WAV files to MP3 when using Long Audio API"
    )
    parser.add_argument(
        "--mp3-bitrate", 
        help="Bitrate for MP3 conversion (default: 64k)"
    )
    parser.add_argument(
        "--sample-rate", type=int,
        help="Audio sample rate in Hz (default: 22050)"
    )
    parser.add_argument(
        "--bit-depth", type=int, choices=[8, 16, 24, 32],
        help="Audio bit depth (default: 16)"
    )
    parser.add_argument(
        "--channels", type=int, choices=[1, 2],
        help="Audio channels (1=mono, 2=stereo) (default: 1)"
    )
    parser.add_argument(
        "--no-skip-existing", action="store_true",
        help="Don't skip existing audio files (by default existing files are skipped)"
    )
    parser.add_argument(
        "--long-audio-timeout", type=int,
        help=f"Timeout in seconds for Long Audio API operations (default: {LONG_AUDIO_TIMEOUT_SECONDS})"
    )
    parser.add_argument(
        "--no-ssml", action="store_true",
        help="Disable SSML processing (by default SSML is enabled)"
    )
    parser.add_argument(
        "--ssml-rules-file", 
        help=f"Path to SSML rules file (default: {SSML_RULES_FILE})"
    )
    parser.add_argument(
        "--markdown-rules-file", 
        help=f"Path to markdown rules file (default: {MARKDOWN_RULES_FILE})"
    )
    parser.add_argument(
        "--debug", action="store_true",
        help="Enable debug logging for detailed information"
    )
    parser.add_argument(
        "--use-ssml", action="store_true",
        help="Use SSML formatting (overrides FORCE_PLAIN_TEXT)"
    )
    args = parser.parse_args()

    # Basic logging setup
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(level=log_level, format="%(levelname)s: %(message)s")
    
    # Add diagnostic information about working directory and file existence
    current_dir = os.getcwd()
    logging.info(f"Current working directory: {current_dir}")
    
    # Check if DEFAULT_INPUT_FILE is set before getting its path
    if DEFAULT_INPUT_FILE:
        default_file_path = DEFAULT_INPUT_FILE
        abs_default_file_path = os.path.abspath(default_file_path)
        file_exists = os.path.exists(default_file_path)
        abs_file_exists = os.path.exists(abs_default_file_path)
        
        logging.info(f"DEFAULT_INPUT_FILE: {default_file_path}")
        logging.info(f"Absolute path: {abs_default_file_path}")
        logging.info(f"File exists (relative path): {file_exists}")
        logging.info(f"File exists (absolute path): {abs_file_exists}")
    else:
        logging.info("DEFAULT_INPUT_FILE is not set")
    
    # Try to list files in current directory to see if the expected file is there
    try:
        files_in_dir = os.listdir(current_dir)
        md_files = [f for f in files_in_dir if f.endswith('.md')]
        logging.info(f"Markdown files in current directory: {md_files}")
    except Exception as e:
        logging.warning(f"Couldn't list directory contents: {e}")
        
    # Determine parameters: Use CLI args if provided, otherwise use defaults
    text_to_synthesize = args.text
    input_file_path = args.input_file
    
    # For output filename, we may derive it from the input file
    output_filename = args.output
    
    lang_code = args.language
    voice = args.voice
    rate = args.speaking_rate
    pitch_val = args.pitch
    preprocess_markdown = not args.no_markdown  # Invert the flag
    exclude_tables = not args.include_tables  # Invert the flag - default is to exclude
    
    # Update global parameters if needed
    def update_globals():
        global MOCK_MODE, AUTO_CONVERT_WAV_TO_MP3, MP3_BITRATE, AUDIO_SAMPLE_RATE, AUDIO_BIT_DEPTH, AUDIO_CHANNELS, SKIP_EXISTING_AUDIO_FILES, LONG_AUDIO_TIMEOUT_SECONDS, USE_SSML, SSML_RULES_FILE, FORCE_PLAIN_TEXT, MARKDOWN_RULES_FILE
        
        # Override MOCK_MODE if specified on command line
        if args.mock:
            MOCK_MODE = True

        # Update AUTO_CONVERT_WAV_TO_MP3 if specified on command line
        if args.no_convert_wav_to_mp3:
            AUTO_CONVERT_WAV_TO_MP3 = False

        # Update MP3_BITRATE if specified on command line
        if args.mp3_bitrate:
            MP3_BITRATE = args.mp3_bitrate

        # Update audio parameters if specified on command line
        if args.sample_rate:
            AUDIO_SAMPLE_RATE = args.sample_rate
        if args.bit_depth:
            AUDIO_BIT_DEPTH = args.bit_depth
        if args.channels:
            AUDIO_CHANNELS = args.channels
            
        # Update SKIP_EXISTING_AUDIO_FILES if specified on command line
        if args.no_skip_existing:
            SKIP_EXISTING_AUDIO_FILES = False
            
        # Update LONG_AUDIO_TIMEOUT_SECONDS if specified on command line
        if args.long_audio_timeout:
            LONG_AUDIO_TIMEOUT_SECONDS = args.long_audio_timeout
            
        # Update SSML settings if specified on command line
        if args.no_ssml:
            USE_SSML = False
        if args.ssml_rules_file:
            SSML_RULES_FILE = args.ssml_rules_file
            
        # Update MARKDOWN_RULES_FILE if specified on command line
        if args.markdown_rules_file:
            MARKDOWN_RULES_FILE = args.markdown_rules_file
            
        # Update FORCE_PLAIN_TEXT if --use-ssml is specified
        if args.use_ssml:
            FORCE_PLAIN_TEXT = False
    
    # Call the function to update globals
    update_globals()

    # Determine whether to save text
    save_text = not args.no_save_text

    # Check the input sources in priority order: CLI args > DEFAULT_INPUT_FOLDER > DEFAULT_INPUT_FILE > DEFAULT_TEXT_INPUT
    
    # First check for CLI-specified input folder
    if args.input_folder:
        logging.info(f"Processing folder specified via CLI: {args.input_folder}")
        if process_folder_input(args.input_folder):
            return  # Exit if folder processing was successful
        else:
            logging.error("Folder processing failed. Exiting.")
            sys.exit(1)
            
    # If no CLI input args, check for default input folder
    if not text_to_synthesize and not input_file_path:
        if DEFAULT_INPUT_FOLDER:
            logging.info(f"Using default input folder: {DEFAULT_INPUT_FOLDER}")
            if process_folder_input(DEFAULT_INPUT_FOLDER):
                return  # Exit if folder processing was successful
            else:
                logging.warning(f"Default folder processing failed, falling back to other input sources")
        
        # Then check for default input file if folder processing failed or not specified
        if DEFAULT_INPUT_FILE and os.path.exists(DEFAULT_INPUT_FILE):
            input_file_path = DEFAULT_INPUT_FILE
            
            # Derive output filename from input file if --output wasn't specified
            if not output_filename:
                # Get the base filename without extension
                base_name = os.path.splitext(os.path.basename(input_file_path))[0]
                # Use the appropriate extension based on audio encoding
                extension = DEFAULT_AUDIO_ENCODING.lower()
                output_filename = f"{base_name}.{extension}"
                logging.info(f"Derived output filename from input file: {output_filename}")
            
            logging.info(f"Using default file: {input_file_path}")
            try:
                with open(input_file_path, 'r', encoding='utf-8') as f:
                    text_to_synthesize = f.read()
                logging.info(f"Successfully read text from default file: {input_file_path}")
            except Exception as e:
                logging.error(f"Error reading default input file: {e}")
                if DEFAULT_TEXT_INPUT is not None:
                    text_to_synthesize = DEFAULT_TEXT_INPUT
                    input_file_path = None
                    logging.warning(f"Falling back to DEFAULT_TEXT_INPUT")
                else:
                    sys.exit(1)
        elif DEFAULT_INPUT_FILE:
            logging.warning(f"Default input file not found: {DEFAULT_INPUT_FILE}")
            if DEFAULT_TEXT_INPUT is not None:
                text_to_synthesize = DEFAULT_TEXT_INPUT
                input_file_path = None  # Set to None to use DEFAULT_TEXT_INPUT project folder
                logging.warning(f"Falling back to DEFAULT_TEXT_INPUT")
            else:
                logging.error("No fallback DEFAULT_TEXT_INPUT available.")
                sys.exit(1)
        elif DEFAULT_TEXT_INPUT is not None:
            text_to_synthesize = DEFAULT_TEXT_INPUT
            input_file_path = None  # Explicitly set to None for DEFAULT_TEXT_INPUT
            logging.info("Using DEFAULT_TEXT_INPUT")
        else:
            logging.error("Error: No input text or file specified via CLI or defaults.")
            sys.exit(1)
    
    # Read from file if specified via CLI
    elif input_file_path and not text_to_synthesize:
        try:
            with open(input_file_path, 'r', encoding='utf-8') as f:
                text_to_synthesize = f.read()
            logging.info(f"Successfully read text from CLI-specified file: {input_file_path}")
        except FileNotFoundError:
            logging.error(f"Error: CLI-specified input file not found: {input_file_path}")
            sys.exit(1)
        except Exception as e:
            logging.error(f"Error reading CLI-specified input file: {e}")
            sys.exit(1)

    if not text_to_synthesize:
        logging.error("Error: No text available for synthesis after checking all sources.")
        sys.exit(1)

    logging.info(f"Final input source: {'File: ' + input_file_path if input_file_path else 'DEFAULT_TEXT_INPUT'}")
    logging.info(f"Text length for synthesis: {len(text_to_synthesize)} characters")

    # If output filename still not set, use a default value
    if not output_filename:
        if DEFAULT_OUTPUT_FILENAME:
            output_filename = DEFAULT_OUTPUT_FILENAME
        else:
            output_filename = "generated_tts_output.mp3"
        logging.info(f"Using output filename: {output_filename}")

    try:
        synthesize_text_to_file(
            text=text_to_synthesize,
            filename=output_filename,
            language_code=lang_code,
            voice_name=voice,
            speaking_rate=rate,
            pitch=pitch_val,
            audio_encoding=DEFAULT_AUDIO_ENCODING,
            preprocess_md=preprocess_markdown,
            exclude_tables=exclude_tables,
            save_text=save_text,
            input_file_path=input_file_path  # Pass the input file path to determine project folder
        )
    except Exception as e:
         # More specific error logging might be helpful depending on expected errors
         logging.error(f"Error during text synthesis processing: {e}")
         # Consider re-raising or sys.exit(1) based on desired script behavior on failure
         sys.exit(1)


if __name__ == "__main__":
    main() 