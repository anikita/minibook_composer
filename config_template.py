"""
TEMPLATE - Configuration settings for the Minibook Composer.

INSTRUCTIONS:
1. Copy this file to 'config.py'
2. Update with your personal settings
3. Keep config.py out of version control (it's in .gitignore)
"""
import os

# API Configuration
API_KEY = os.environ.get('GOOGLE_API_KEY', '')  # Set your API key here or use environment variable

# Path Configuration
# Update this to your preferred output location
OUTPUT_FOLDER = os.path.join(os.path.expanduser("~"), "Documents/Minibooks")

# Project folder for storing all generated books and their source files
PROJECT_FOLDER = "MyBooks"

# Model Configuration
MODEL = 'gemini-2.5-flash-preview-04-17'  # Options: gemini-2.5-flash-preview-04-17, gemini-2.0-flash
TEMPERATURE = 0.7
TOP_P = 0.95

# MD to EPUB Converter Configuration
# By default, use the same folder as the minibook output
MD_TO_EPUB_INPUT_DIR = OUTPUT_FOLDER
MD_TO_EPUB_OUTPUT_DIR = OUTPUT_FOLDER 