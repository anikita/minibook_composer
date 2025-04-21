# Minibook Composer

A Python tool that automatically generates comprehensive minibooks on any topic using Google's Gemini AI. The tool creates a structured book with chapters, saving both intermediate outputs and the final compiled book.

## Features

- Creates a complete minibook from a single topic
- Generates chapter outlines first, then elaborates on each chapter
- Organizes content into a logical structure with a table of contents
- Supports dynamic chapter count based on selected instruction templates
- Customizable narrative styles (analogies, character-driven, story arc, etc.)
- Various pedagogical approaches (scaffolded, socratic, project-based, spiral)
- Saves all intermediate steps for review and inspection
- Creates separate project folders for each book topic
- Configurable base chapter count and API request timing
- Option to save final outputs to a separate collection folder
- Secure configuration system for API keys and personal paths

## Requirements

- Python 3.7+
- Google API key for Gemini

## Installation

1. Install the required package:

```bash
pip install google-generativeai
```

2. Set up your configuration:
   - Copy `config_template.py` to `config.py`
   - Update `config.py` with your personal settings
   - Add your Google API key to `config.py` or set it as an environment variable:
     ```bash
     export GOOGLE_API_KEY="your-api-key-here"
     ```

## Configuration

The application uses a separate configuration file (`config.py`) for sensitive or user-specific settings:

```python
# Copy this from config_template.py and customize
API_KEY = os.environ.get('GOOGLE_API_KEY', 'your-key-here')  # Your API key
OUTPUT_FOLDER = os.path.join(os.path.expanduser("~"), "Documents/Minibooks")  # Your output path
PROJECT_FOLDER = "MyBooks"  # Where to store project files
MODEL = 'gemini-2.5-flash-preview-04-17'  # AI model to use
TEMPERATURE = 0.7  # Model temperature setting
TOP_P = 0.95  # Model top_p setting
```

This approach keeps sensitive information out of version control. If `config.py` is not found, the application falls back to default settings.

## Usage

### Command Line

Create a minibook on a specific topic:

```bash
python minibook_composer.py --topic "Introduction to Quantum Computing"
```

Customize the narrative style and pedagogical approach:

```bash
python minibook_composer.py --topic "Machine Learning Basics" --narrative-style analogies --pedagogical-approach scaffolded
```

Use a specific type of analogy:

```bash
python minibook_composer.py --topic "Investing Principles" --narrative-style analogies_sports
```

List all available narrative styles:

```bash
python minibook_composer.py --list-styles
```

List all available pedagogical approaches:

```bash
python minibook_composer.py --list-approaches
```

Use dynamic chapter count with specific instruction templates:

```bash
python minibook_composer.py --topic "Space Exploration" --num-chapters dynamic --add-instructions history future key_terms
```

Set a custom base chapter count for dynamic mode:

```bash
python minibook_composer.py --topic "Artificial Intelligence" --base-chapters 4
```

Save final books to a custom output folder:

```bash
python minibook_composer.py --topic "Space Exploration" --output-folder "Completed_Books"
```

Use the default topic and settings:

```bash
python minibook_composer.py
```

### Command Line Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--topic` | The topic for the minibook | "Storytelling in Science Education, a practical guide" |
| `--api-key` | Google API key | From config.py or environment variable |
| `--num-chapters` | Number of chapters to generate | "dynamic" |
| `--base-chapters` | Base number of chapters when using dynamic mode | 3 |
| `--chapter-delay` | Wait time in seconds between chapter requests | 1 |
| `--output-folder` | Folder to store final markdown files | From config.py |
| `--add-instructions` | Add specific instruction templates | None |
| `--custom-instructions` | Add custom additional instructions | None |
| `--no-summary` | Skip generating a summary chapter | False |
| `--narrative-style` | Narrative style to use throughout the book | None |
| `--pedagogical-approach` | Pedagogical approach to structure the content | None |
| `--list-styles` | List all available narrative styles and exit | False |
| `--list-approaches` | List all available pedagogical approaches and exit | False |

### Narrative Styles

The minibook composer supports several narrative styles that can be applied throughout the book:

| Style | Description |
|-------|-------------|
| `analogies` | Uses analogies and metaphors to explain complex concepts |
| `analogies_sports` | Uses sports-related analogies to explain concepts |
| `analogies_cooking` | Uses cooking-related analogies to explain concepts |
| `analogies_business` | Uses business-related analogies to explain concepts |
| `character_driven` | Introduces fictional or real guides/characters to explain concepts |
| `problem_solution` | Frames content as challenges with stepwise solutions |
| `story_arc` | Uses a classic beginning-middle-end story structure |

### Pedagogical Approaches

You can structure the educational content with different pedagogical approaches:

| Approach | Description |
|----------|-------------|
| `scaffolded` | Progressive disclosure, building on previous knowledge |
| `socratic` | Guide learning through questioning and critical thinking |
| `project_based` | Structure content around a hands-on project or example |
| `spiral` | Revisit key ideas with increasing depth |

### Dynamic Chapter Count

The dynamic chapter count feature automatically calculates the appropriate number of chapters based on:

1. A base count (default: 3)
2. Additional chapters from instruction templates

The following instruction templates will each add one chapter:
- `history` - Adds a chapter about the history of the topic
- `key_terms` - Adds a chapter about key terms and definitions
- `interdisciplinary` - Adds a chapter about relations to other disciplines
- `future` - Adds a chapter about future developments
- `applications` - Adds a chapter about practical applications
- `controversies` - Adds a chapter about debates in the field
- `key_figures` - Adds a chapter about key contributors
- `methodologies` - Adds a chapter about research methodologies

### Running from IDE

For direct execution in an IDE, simply uncomment and modify these lines at the bottom of the script:

```python
# For direct execution in IDE, uncomment and modify these lines:
topic = "Introduction to Blockchain Technology"
api_key = "your-api-key-here"  # Or use environment variable
create_minibook(topic, api_key)
```

### Customizing Prompts

All AI prompts are stored in `lib_prompts.py` for easy customization:

1. Open `lib_prompts.py` in your text editor
2. Modify the prompts in the `PROMPTS` dictionary
3. Keep the format strings (like `{topic}`, `{chapter_title}`, `{num_chapters}`) intact
4. Modify the narrative styles in `NARRATIVE_STYLES` dictionary
5. Modify the pedagogical approaches in `PEDAGOGICAL_APPROACHES` dictionary
6. Save and run the script as usual

You can also customize the default instruction templates by modifying the `INSTRUCTION_TEMPLATES` dictionary.

### Configuration

You can modify the default settings by editing the global variables at the top of `minibook_composer.py`:

```python
# User parameters
TOPIC = "Storytelling in Science Education, a practical guide"

# Default instruction templates to use when none are provided by command line
SELECTED_INSTRUCTIONS = ["key_terms", "history", "future"]

# Add additional instructions for the AI here
ADDITIONAL_INSTRUCTIONS = """
-Explain strategies and options around narrative structure
-Make it a practical guide for advanced scientist and engineers to communicate complex concepts to non-technical audiences
"""

NUM_CHAPTERS = 'dynamic'  # Can be a number or 'dynamic' to calculate based on instructions
BASE_CHAPTER_COUNT = 3    # Base number of chapters when using dynamic mode

# Default narrative style and pedagogical approach
NARRATIVE_STYLE = None  # e.g., "analogies", "character_driven", etc.
PEDAGOGICAL_APPROACH = None  # e.g., "scaffolded", "socratic", etc.
```

## Output Structure

For each topic, the script creates a project folder with the following structure:

```
MyBooks/
└── topic_name_timestamp/
    ├── outline.md             # The initial book outline
    ├── metadata.json          # Project metadata
    ├── minibook_topic_name.md # The final compiled book
    └── chapters/              # Individual chapter content
        ├── chapter_1_*.md
        ├── chapter_2_*.md
        └── ...
```

Additionally, a copy of the final book is stored in the output folder.

## How It Works

1. The script sends a prompt to Gemini to create a detailed book outline with the specified number of chapters
   - If using dynamic mode, it calculates the number of chapters based on instructions
2. It parses the outline to identify chapters
3. For each chapter, it sends a new prompt asking for elaboration (with configurable delay between requests)
   - Both the outline and chapter content include the specified narrative style and pedagogical approach
4. All chapter responses are compiled into a single markdown file
5. The final book includes a table of contents with links to each chapter

## Example

```bash
python minibook_composer.py --topic "Sustainable Urban Planning" --narrative-style problem_solution --pedagogical-approach project_based
```

This will create a project folder containing a complete minibook on sustainable urban planning, using a problem-solution narrative style and project-based pedagogical approach.

## Additional Utilities

### Markdown to EPUB Converter

The repository includes a standalone utility script (`md_to_epub_converter.py`) that can convert Markdown files to EPUB format. This is useful for creating e-reader friendly versions of your minibooks.

#### Requirements
- Python 3.7+
- Pandoc must be installed on your system (https://pandoc.org/installing.html)

#### Configuration

The converter uses the same `config.py` file as the main application for its input and output directories:

```python
# MD to EPUB Converter Configuration
MD_TO_EPUB_INPUT_DIR = OUTPUT_FOLDER  # Directory to scan for markdown files
MD_TO_EPUB_OUTPUT_DIR = OUTPUT_FOLDER  # Directory to save EPUB files
```

If `config.py` is not found, the script will use default directories.

#### Usage

Convert all markdown files in a directory:
```bash
python md_to_epub_converter.py /path/to/markdown/files --output-dir /path/to/output
```

Convert a single markdown file:
```bash
python md_to_epub_converter.py --single-file /path/to/file.md --title "My Custom Title"
```

Additional options:
```bash
# Scan directory recursively
python md_to_epub_converter.py /path/to/markdown/files --recursive

# Specify a custom output directory
python md_to_epub_converter.py /path/to/markdown/files --output-dir /path/to/output
```

The converter automatically adds a table of contents to make navigation easier on e-readers. 