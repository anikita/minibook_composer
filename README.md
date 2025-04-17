# Minibook Composer

A Python tool that automatically generates comprehensive minibooks on any topic using Google's Gemini AI. The tool creates a structured book with chapters, saving both intermediate outputs and the final compiled book.

## Features

- Creates a complete minibook from a single topic
- Generates chapter outlines first, then elaborates on each chapter
- Organizes content into a logical structure with a table of contents
- Saves all intermediate steps for review and inspection
- Creates separate project folders for each book topic
- Customizable prompts in a centralized file

## Requirements

- Python 3.7+
- Google API key for Gemini

## Installation

1. Install the required package:

```bash
pip install google-generativeai
```

2. Set up your Google API key:
   - Create a Google API key at https://makersuite.google.com/app/apikey
   - Either set it as an environment variable:
     ```bash
     export GOOGLE_API_KEY="your-api-key-here"
     ```
   - Or provide it directly when running the script

## Usage

### Command Line

Create a minibook on a specific topic:

```bash
python minibook_composer.py --topic "Introduction to Quantum Computing" --api-key "your-api-key-here"
```

Use the default topic ("Machine Learning Fundamentals"):

```bash
python minibook_composer.py
```

### Running from IDE

For direct execution in an IDE, simply uncomment and modify these lines at the top of the script:

```python
# For direct execution in IDE, uncomment and modify these lines:
topic = "Introduction to Blockchain Technology"
api_key = "your-api-key-here"  # Or use environment variable
create_minibook(topic, api_key)
```

### Customizing Prompts

All AI prompts are stored in `prompts.py` for easy customization:

1. Open `prompts.py` in your text editor
2. Modify the prompts in the `PROMPTS` dictionary
3. Keep the format strings (like `{topic}`, `{chapter_title}`) intact
4. Save and run the script as usual

You can fine-tune the prompts to adjust the AI's style, format, and content generation without touching the main code.

## Output Structure

For each topic, the script creates a project folder with the following structure:

```
topic_name_timestamp/
├── outline.md             # The initial book outline
├── metadata.json          # Project metadata
├── minibook_topic_name.md # The final compiled book
└── chapters/              # Individual chapter content
    ├── chapter_1_*.md
    ├── chapter_2_*.md
    └── ...
```

## How It Works

1. The script sends a prompt to Gemini to create a detailed book outline
2. It parses the outline to identify chapters
3. For each chapter, it sends a new prompt asking for elaboration
4. All chapter responses are compiled into a single markdown file
5. The final book includes a table of contents with links to each chapter

## Example

```bash
python minibook_composer.py --topic "Sustainable Urban Planning"
```

This will create a project folder containing a complete minibook on sustainable urban planning, with chapters covering different aspects of the topic. 