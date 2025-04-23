import os
import re
import json
import shutil
import sys
import google.generativeai as genai
from datetime import datetime
import argparse
import time
from lib_prompts import (
    PROMPTS, get_outline_prompt, INSTRUCTION_TEMPLATES, get_instruction_templates,
    NARRATIVE_STYLES, PEDAGOGICAL_APPROACHES, apply_style_and_approach,
    get_available_styles, get_available_approaches
)

# Import user-specific configuration if available
try:
    from config import API_LLM_KEY, OUTPUT_FOLDER, PROJECT_FOLDER, MODEL, TEMPERATURE, TOP_P
    print("Using configuration from config.py")
except ImportError:
    print("Config file not found. Using default configuration.")
    # Default configuration if config.py is not available
    API_LLM_KEY = os.environ.get('GOOGLE_API_KEY', '')
    OUTPUT_FOLDER = os.path.join(os.path.expanduser("~"), "Documents/Minibooks")
    PROJECT_FOLDER = "MyBooks"
    MODEL = 'gemini-2.5-flash-preview-04-17'
    TEMPERATURE = 0.7
    TOP_P = 0.95

# Build your own minibook
# Set your key, set your topic, go!

# User parameters
TOPIC = "Taxonomy: Organizing the Building Blocks of Thought"

# Default instruction templates to use when none are provided by command line
SELECTED_OUTLINE_INSTRUCTIONS = ["conclusion", "formal_theories","philosophy"] # Instructions for the outline generation
SELECTED_CHAPTER_INSTRUCTIONS = ["summary_tables"] # Instructions for chapter generation

# Custom instructions that will ALWAYS be added alongside template instructions (only for outline)
CUSTOM_INSTRUCTIONS = """ 
 
"""

# Default narrative style and pedagogical approach
NARRATIVE_STYLE = None  # e.g., "analogies", "character_driven", "problem_solution", "story_arc"
PEDAGOGICAL_APPROACH = "socratic"  # e.g., "scaffolded", "socratic", "project_based", "spiral"

NUM_CHAPTERS = 'dynamic'  # Can be a number or 'dynamic' to calculate based on instructions
BASE_CHAPTER_COUNT = 4    # Base number of chapters when using dynamic mode
CHAPTER_DELAY = 1  # Default wait time in seconds between chapter requests

def setup_genai(api_llm_key):
    """Initialize the Gemini API with the provided API key."""
    if not api_llm_key:
        raise ValueError("API_LLM_KEY is missing. Please set it in config.py or via GOOGLE_API_KEY environment variable.")
    genai.configure(api_key=api_llm_key)
    return genai.GenerativeModel(MODEL)

def sanitize_filename(text, max_length=50):
    """Generate a safe filename from text."""
    # Remove special characters and replace spaces with underscores
    sanitized = re.sub(r'[^a-zA-Z0-9 ]', '', text)
    words = sanitized.split()
    
    # Take first few words to create a concise filename
    if len(words) > 5:
        words = words[:5]
    
    filename = "_".join(words).lower()
    
    # Truncate if too long
    if len(filename) > max_length:
        filename = filename[:max_length]
        
    return filename

def create_project_folder(topic):
    """Create a project folder for the topic."""
    folder_name = sanitize_filename(topic)
    timestamp = datetime.now().strftime("%y%m%d_%H%M")
    project_name = f"{folder_name}_{timestamp}"
    
    # Ensure the base project folder exists
    if not os.path.exists(PROJECT_FOLDER):
        os.makedirs(PROJECT_FOLDER, exist_ok=True)

    project_path = os.path.join(PROJECT_FOLDER, project_name)
    
    # Create project directory and subdirectories
    os.makedirs(project_path, exist_ok=True)
    os.makedirs(os.path.join(project_path, "chapters"), exist_ok=True)
    
    return project_path

def ask_gemini(model, prompt, max_retries=3, retry_delay=3):
    """Send a prompt to Gemini and get the response."""
    retry_count = 0
    while retry_count <= max_retries:
        try:
            response = model.generate_content(
                prompt,
                generation_config={
                    "temperature": TEMPERATURE,
                    "top_p": TOP_P,
                    "response_mime_type": "text/plain",
                }
            )
            return response.text
        except Exception as e:
            if "ResourceExhausted" in str(e) or "429" in str(e):
                retry_count += 1
                wait_time = retry_delay * (2 ** retry_count)  # Exponential backoff
                print(f"Rate limit reached. Waiting {wait_time} seconds before retrying...")
                time.sleep(wait_time)
                if retry_count > max_retries:
                    print("Maximum retries reached. Returning partial response.")
                    return "API rate limit exceeded. This content could not be generated."
            else:
                raise e

def save_to_file(content, filepath):
    """Save content to a file."""
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Saved to {filepath}")

def calculate_dynamic_chapter_count(base_chapters, instructions):
    """Calculate a dynamic chapter count based on instructions."""
    # Default base chapter count
    if isinstance(base_chapters, int):
        chapter_count = base_chapters
    else:
        # Start with default base chapter count if not an integer
        chapter_count = BASE_CHAPTER_COUNT
    
    # Count additional chapters from instructions
    additional_chapters = 0
    chapter_adding_instructions = [
        "history", "key_terms", "interdisciplinary", "future", 
        "applications", "controversies", "key_figures", "methodologies"
    ]
    
    # Process list of instruction template keys
    if isinstance(instructions, list):
        for instruction in instructions:
            if instruction in chapter_adding_instructions:
                additional_chapters += 1
    
    # Process custom instruction string
    elif isinstance(instructions, str):
        # Count "add a chapter" phrases in custom instructions
        add_chapter_count = instructions.lower().count("add a chapter")
        additional_chapters += add_chapter_count
    
    # Ensure a reasonable minimum and maximum
    total_chapters = max(3, min(15, chapter_count + additional_chapters))
    return total_chapters

def generate_book_outline_prompt(topic, num_chapters, additional_instructions=None, base_chapters=BASE_CHAPTER_COUNT):
    """Generate the prompt for creating a book outline with optional additional instructions."""
    # Get the base outline prompt
    outline_prompt = get_outline_prompt()
    
    # Determine the actual number of chapters to use
    if num_chapters == 'dynamic':
        actual_num_chapters = calculate_dynamic_chapter_count(base_chapters, additional_instructions)
    else:
        actual_num_chapters = num_chapters
    
    # Process additional instructions
    formatted_instructions = ""
    
    # First, handle the templated instructions if provided
    if additional_instructions:
        # If it's a list of keys from INSTRUCTION_TEMPLATES
        if isinstance(additional_instructions, list) and additional_instructions:
            instructions_text = []
            for key in additional_instructions:
                if key in INSTRUCTION_TEMPLATES:
                    instructions_text.append("- " + INSTRUCTION_TEMPLATES[key])
            
            if instructions_text:
                formatted_instructions += "\n\nAdditional instructions:\n" + "\n".join(instructions_text)
        
        # If it's a string (from command line --custom-instructions), use it directly
        elif isinstance(additional_instructions, str) and additional_instructions.strip():
            formatted_instructions += "\n\nAdditional instructions:\n" + additional_instructions
    
    # Then, always append CUSTOM_INSTRUCTIONS if it's not empty
    if CUSTOM_INSTRUCTIONS and CUSTOM_INSTRUCTIONS.strip():
        # Add a separator if we already have some instructions
        if formatted_instructions:
            formatted_instructions += "\n\nCustom focus:\n" + CUSTOM_INSTRUCTIONS.strip()
        else:
            formatted_instructions += "\n\nAdditional instructions:\n" + CUSTOM_INSTRUCTIONS.strip()
    
    # Add all formatted instructions to the prompt
    if formatted_instructions:
        outline_prompt += formatted_instructions
    
    # Format the final prompt with topic and num_chapters
    return outline_prompt.format(topic=topic, num_chapters=actual_num_chapters)

def generate_book_outline(model, topic, project_path, num_chapters, outline_instructions=None, 
                         base_chapters=BASE_CHAPTER_COUNT):
    """Generate a book outline for the given topic."""
    outline_prompt = generate_book_outline_prompt(
        topic, num_chapters, outline_instructions, base_chapters
    )
    
    outline = ask_gemini(model, outline_prompt)
    
    # Save the outline
    outline_path = os.path.join(project_path, "outline.md")
    save_to_file(outline, outline_path)
    
    return outline

def parse_chapters(outline):
    """Parse the outline to extract chapters."""
    chapters = []
    
    # Look for chapter headings with various patterns
    # First try to find numbered chapter patterns like "Chapter 1:" or "1. Chapter:"
    chapter_patterns = [
        r'#+\s*Chapter\s+\d+[:.]\s*(.*?)(?=\n)',  # "## Chapter 1: Title"
        r'#+\s*\d+[:.]\s*Chapter[:.]\s*(.*?)(?=\n)',  # "## 1. Chapter: Title"
        r'#+\s*\d+[:.]\s*(.*?)(?=\n)',  # "## 1. Title"
        r'\*\*(\d+)\.\s*Chapter\s+\d*[:.]\s*(.*?)\*\*',  # "**1. Chapter 1: Title**"
        r'\*\*Chapter\s+(\d+)[:.]\s*(.*?)\*\*',  # "**Chapter 1: Title**"
        r'\*\*(\d+)[:.]\s*(.*?)\*\*'  # "**1. Title**"
    ]
    
    # Check if we have a "Minibook Title" at the beginning
    title_match = re.search(r'#+\s*Minibook Title[:.]\s*(.*?)(?=\n)', outline, re.IGNORECASE)
    book_title = title_match.group(1).strip() if title_match else "Untitled"
    
    # Try each pattern until we find matches
    all_matches = []
    for pattern in chapter_patterns:
        matches = re.findall(pattern, outline, re.IGNORECASE | re.DOTALL)
        if matches:
            # Handle different match group structures
            if isinstance(matches[0], tuple):
                # Some patterns return tuples (e.g., when there are multiple capture groups)
                matches = [m[-1] for m in matches]  # Get the last group which should be the title
            all_matches.extend(matches)
            break
    
    # If no matches found with chapter patterns, look for any numbered sections
    if not all_matches:
        # Look for "**N. Title**" pattern commonly used in outlines
        matches = re.findall(r'\*\*(\d+)[:.]\s*(.*?)\*\*', outline)
        if matches:
            all_matches = [title for _, title in matches]
    
    # If still no matches, try to find any headings
    if not all_matches:
        # Look for markdown headings that aren't the title
        headings = re.findall(r'##\s+(.*?)(?=\n)', outline)
        # Filter out common non-chapter headings
        filtered_headings = [h for h in headings if not any(x in h.lower() for x in 
                             ['minibook title', 'table of contents', 'introduction', 'conclusion', 
                              'overview', 'summary', 'about'])]
        all_matches = filtered_headings
    
    # Process each chapter
    chapter_content_parts = []
    for i, title in enumerate(all_matches):
        # Try to find the content for this chapter
        title_pattern = re.escape(title.strip())
        
        # Find where this chapter starts in the text
        title_pos = re.search(title_pattern, outline, re.IGNORECASE)
        if not title_pos:
            content = ""  # No content found
        else:
            start_pos = title_pos.end()
            
            # Find the next chapter title or end of text
            if i < len(all_matches) - 1:
                next_title = re.escape(all_matches[i+1].strip())
                next_pos = re.search(next_title, outline[start_pos:], re.IGNORECASE)
                if next_pos:
                    content = outline[start_pos:start_pos + next_pos.start()].strip()
                else:
                    content = outline[start_pos:].strip()
            else:
                # Last chapter
                content = outline[start_pos:].strip()
        
        # Look for bullet points after the title
        bullet_points = re.findall(r'^\s*\*\s*(.*?)$', content, re.MULTILINE)
        if bullet_points:
            content = "\n".join([f"* {point}" for point in bullet_points])
        
        chapters.append({
            "title": title.strip(),
            "outline": content
        })
    
    # If we couldn't extract chapters properly but the outline exists
    if not chapters and outline:
        # Use the whole outline as a single chapter
        chapters.append({
            "title": book_title,
            "outline": outline
        })
    
    return chapters

def elaborate_chapter(model, chapter, project_path, index, delay=CHAPTER_DELAY, 
                     narrative_style=None, pedagogical_approach=None, chapter_instructions=None):
    """Generate detailed content for a chapter based on its outline, and return the prompt used."""
    chapter_title = chapter["title"]
    chapter_outline = chapter["outline"]
    
    # Get the base prompt
    prompt_template = PROMPTS["chapter_elaboration"]
    
    # Format the base prompt BEFORE applying style/approach
    # to ensure formatting placeholders are filled
    formatted_prompt = prompt_template.format(
        chapter_number=index+1,
        chapter_title=chapter_title,
        chapter_outline=chapter_outline
    )
    
    # Add chapter-specific instructions if provided
    if chapter_instructions:
        # If it's a list of keys from INSTRUCTION_TEMPLATES
        if isinstance(chapter_instructions, list) and chapter_instructions:
            instructions_text = []
            for key in chapter_instructions:
                if key in INSTRUCTION_TEMPLATES:
                    instructions_text.append("- " + INSTRUCTION_TEMPLATES[key])
            
            if instructions_text:
                formatted_prompt += "\n\nAdditional chapter instructions:\n" + "\n".join(instructions_text)
        
        # If it's a string, use it directly
        elif isinstance(chapter_instructions, str) and chapter_instructions.strip():
            formatted_prompt += "\n\nAdditional chapter instructions:\n" + chapter_instructions
    
    # Apply narrative style and pedagogical approach if specified
    final_prompt = apply_style_and_approach(formatted_prompt, narrative_style, pedagogical_approach)
    
    # Add a delay before each API call to avoid rate limiting
    if delay > 0:
        print(f"Waiting {delay} seconds before requesting content for Chapter {index+1}...")
        time.sleep(delay)
    
    chapter_content = ask_gemini(model, final_prompt)
    
    # Create chapter filename
    safe_chapter_title = sanitize_filename(chapter_title)
    chapter_filename = f"chapter_{index+1}_{safe_chapter_title}.md"
    chapter_path = os.path.join(project_path, "chapters", chapter_filename)
    
    # Save chapter content
    save_to_file(chapter_content, chapter_path)
    
    # Also save the prompt used for this chapter for debugging purposes
    prompt_filename = f"prompt_{index+1}_{safe_chapter_title}.txt"
    prompt_path = os.path.join(project_path, "chapters", prompt_filename)
    save_to_file(final_prompt, prompt_path)
    
    return {
        "title": chapter_title,
        "content": chapter_content,
        "file": chapter_path,
        "prompt": final_prompt,
        "prompt_file": prompt_path
    }

def merge_chapters(chapters, topic, project_path, output_folder=None):
    """Merge all chapter contents into a single markdown file."""
    book_title = f"# Minibook: {topic}\n\n"
    toc = "## Table of Contents\n\n"
    
    # Build table of contents
    for i, chapter in enumerate(chapters):
        toc += f"{i+1}. [{chapter['title']}](#chapter-{i+1})\n"
    
    toc += "\n---\n\n"
    
    # Build book content
    book_content = book_title + toc
    
    for i, chapter in enumerate(chapters):
        book_content += f"<a name='chapter-{i+1}'></a>\n\n"
        
        # Check if the content already starts with the chapter heading
        chapter_heading = f"## Chapter {i+1}: {chapter['title']}"
        chapter_content = chapter['content']
        
        # If the content doesn't already start with the correct chapter heading, add it
        if not chapter_content.strip().startswith(chapter_heading):
            book_content += f"{chapter_heading}\n\n"
        
        book_content += chapter_content
        book_content += "\n\n---\n\n"
    
    # Create the final book filename
    safe_topic = sanitize_filename(topic)
    book_filename = f"minibook_{safe_topic}.md"
    
    # Save the complete book in the project folder
    book_path = os.path.join(project_path, book_filename)
    save_to_file(book_content, book_path)
    
    # Also save to output folder if specified
    if output_folder:
        # Ensure output folder exists
        os.makedirs(output_folder, exist_ok=True)
        
        # Create a more descriptive filename with timestamp for the output folder
        timestamp = datetime.now().strftime("%y%m%d_%H%M")
        output_filename = f"minibook_{safe_topic}_{timestamp}.md"
        output_path = os.path.join(output_folder, output_filename)
        
        # Save to output folder
        save_to_file(book_content, output_path)
        print(f"Final book also saved to: {output_path}")
        
        # Return both paths
        return book_path, output_path
    
    return book_path

def save_metadata(topic, project_path, chapters, outline_prompt=None, instructions=None, 
                 num_chapters=None, narrative_style=None, pedagogical_approach=None):
    """Save metadata about the project for future reference."""
    metadata = {
        "topic": topic,
        "created_at": datetime.now().isoformat(),
        # Include title, file, and prompt for each chapter
        "chapters": [
            {
                "title": chapter["title"],
                "file": os.path.basename(chapter["file"]),
                "prompt": chapter.get("prompt", "Prompt not captured"),
                "prompt_file": os.path.basename(chapter.get("prompt_file", ""))
            }
            for chapter in chapters
        ],
        "model": MODEL,
        "temperature": TEMPERATURE,
        "top_p": TOP_P,
        "settings": {
            "num_chapters": num_chapters or NUM_CHAPTERS,
            "chapter_delay": CHAPTER_DELAY,
            "narrative_style": narrative_style,
            "pedagogical_approach": pedagogical_approach
        }
    }
    
    # Include instructions if available
    if instructions:
        if isinstance(instructions, dict):
            # New format with separate outline and chapter instructions
            metadata["instructions"] = {
                "outline": [],
                "chapter": []
            }
            
            # Process outline instructions
            if "outline" in instructions and instructions["outline"]:
                if isinstance(instructions["outline"], list):
                    outline_instr = []
                    for key in instructions["outline"]:
                        if key in INSTRUCTION_TEMPLATES:
                            outline_instr.append(INSTRUCTION_TEMPLATES[key])
                    metadata["instructions"]["outline"] = outline_instr
                elif isinstance(instructions["outline"], str):
                    metadata["instructions"]["outline"] = instructions["outline"]
            
            # Process chapter instructions
            if "chapter" in instructions and instructions["chapter"]:
                if isinstance(instructions["chapter"], list):
                    chapter_instr = []
                    for key in instructions["chapter"]:
                        if key in INSTRUCTION_TEMPLATES:
                            chapter_instr.append(INSTRUCTION_TEMPLATES[key])
                    metadata["instructions"]["chapter"] = chapter_instr
                elif isinstance(instructions["chapter"], str):
                    metadata["instructions"]["chapter"] = instructions["chapter"]
        
        elif isinstance(instructions, list):
            # Legacy format - treat as outline instructions
            instructions_text = []
            for key in instructions:
                if key in INSTRUCTION_TEMPLATES:
                    instructions_text.append(INSTRUCTION_TEMPLATES[key])
            metadata["instructions"] = instructions_text
        
        elif isinstance(instructions, str):
            # String instructions
            metadata["instructions"] = instructions
    
    # Include the outline prompt if available
    if outline_prompt:
        metadata["outline_prompt"] = outline_prompt
        
        # Also save outline prompt to a separate file for easier access
        outline_prompt_path = os.path.join(project_path, "outline_prompt.txt")
        save_to_file(outline_prompt, outline_prompt_path)
        metadata["outline_prompt_file"] = "outline_prompt.txt"
    
    metadata_path = os.path.join(project_path, "metadata.json")
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"Metadata saved to {metadata_path}")

def create_minibook(topic, api_llm_key, num_chapters, chapter_delay=CHAPTER_DELAY, 
                   output_folder=OUTPUT_FOLDER, add_summary=True, outline_instructions=None, 
                   chapter_instructions=None, base_chapters=BASE_CHAPTER_COUNT, 
                   narrative_style=None, pedagogical_approach=None):
    """Main function to create a minibook on the given topic."""
    if not api_llm_key:
        raise ValueError("Please provide a Google API key (for LLM) either as an argument or by setting the GOOGLE_API_KEY environment variable or in config.py.")
    
    # Handle 'dynamic' chapter count
    if num_chapters == 'dynamic':
        # The actual number will be calculated in generate_book_outline_prompt
        actual_num_chapters = 'dynamic'
    else:
        # Try to convert to integer if it's a string representing a number
        try:
            actual_num_chapters = int(num_chapters)
        except (ValueError, TypeError):
            print(f"Warning: Invalid num_chapters value '{num_chapters}'. Using {base_chapters} as default.")
            actual_num_chapters = base_chapters
    
    # Initialize Gemini model
    model = setup_genai(api_llm_key)
    
    # Create project folder
    project_path = create_project_folder(topic)
    print(f"Created project folder: {project_path}")
    
    # Generate book outline
    print(f"Generating outline for: {topic}")
    outline_prompt = generate_book_outline_prompt(
        topic, actual_num_chapters, outline_instructions, base_chapters
    )
    outline = generate_book_outline(
        model, topic, project_path, actual_num_chapters, 
        outline_instructions, base_chapters
    )
    
    # Parse chapters from outline
    chapters = parse_chapters(outline)
    print(f"Extracted {len(chapters)} chapters from outline")
    
    # Process each chapter
    processed_chapters = []
    for i, chapter in enumerate(chapters):
        print(f"Elaborating on Chapter {i+1}: {chapter['title']}")
        try:
            processed_chapter = elaborate_chapter(
                model, chapter, project_path, i, chapter_delay,
                narrative_style, pedagogical_approach, chapter_instructions
            )
            processed_chapters.append(processed_chapter)
        except Exception as e:
            print(f"Error processing chapter {i+1}: {str(e)}")
            # Create a placeholder for the failed chapter
            safe_chapter_title = sanitize_filename(chapter["title"])
            chapter_filename = f"chapter_{i+1}_{safe_chapter_title}.md"
            chapter_path = os.path.join(project_path, "chapters", chapter_filename)
            error_content = f"# {chapter['title']}\n\nError generating content: {str(e)}\n\nOutline:\n{chapter['outline']}"
            save_to_file(error_content, chapter_path)
            
            # Also create a placeholder for the failed prompt
            prompt_filename = f"prompt_{i+1}_{safe_chapter_title}.txt" 
            prompt_path = os.path.join(project_path, "chapters", prompt_filename)
            error_prompt = f"Error generating prompt: {str(e)}\n\nOutline that would have been used:\n{chapter['outline']}"
            save_to_file(error_prompt, prompt_path)
            
            processed_chapters.append({
                "title": chapter["title"],
                "content": error_content,
                "file": chapter_path,
                "prompt": "Error generating prompt due to: " + str(e),
                "prompt_file": prompt_path
            })
    
    # Merge chapters into complete book
    print("Merging chapters into final book")
    result = merge_chapters(processed_chapters, topic, project_path, output_folder)
    
    # Handle the different return types
    if isinstance(result, tuple):
        book_path, output_path = result
    else:
        book_path = result
        output_path = None
    
    # Save project metadata
    save_metadata(
        topic, project_path, processed_chapters, outline_prompt, 
        {"outline": outline_instructions, "chapter": chapter_instructions}, 
        actual_num_chapters, narrative_style, pedagogical_approach
    )
    
    print(f"\nMinibook creation complete!")
    print(f"Project folder: {project_path}")
    print(f"Final book: {book_path}")
    if output_path:
        print(f"Output copy: {output_path}")
    
    return project_path, book_path

# For direct execution in IDE, uncomment and modify these lines:
# topic = "Introduction to Blockchain Technology"
# api_key = "your-api-key-here"  # Or use environment variable
# create_minibook(topic, api_key)

def main():
    # Get all available narrative styles and pedagogical approaches
    narrative_styles = get_available_styles()
    pedagogical_approaches = get_available_approaches()
    
    parser = argparse.ArgumentParser(description='Create a minibook on a specified topic using AI.')
    parser.add_argument('--topic', type=str, default=TOPIC, 
                        help=f'The topic for the minibook (default: "{TOPIC}")')
    parser.add_argument('--api-key', type=str, default=API_LLM_KEY,
                        help='Google API key for the LLM (or set GOOGLE_API_KEY environment variable)')
    parser.add_argument('--num-chapters', default=NUM_CHAPTERS,
                        help=f'The suggested number of chapters to produce in the outline (default: {NUM_CHAPTERS}). Can be a number or "dynamic"')
    parser.add_argument('--base-chapters', type=int, default=BASE_CHAPTER_COUNT,
                        help=f'Base number of chapters when using dynamic mode (default: {BASE_CHAPTER_COUNT})')
    parser.add_argument('--chapter-delay', type=int, default=CHAPTER_DELAY,
                        help=f'Wait time in seconds between chapter requests (default: {CHAPTER_DELAY})')
    parser.add_argument('--output-folder', type=str, default=OUTPUT_FOLDER,
                        help=f'Folder to store final markdown files (default: {OUTPUT_FOLDER})')
    parser.add_argument('--no-summary', action='store_true',
                        help='Skip generating a summary chapter')
    parser.add_argument('--outline-instructions', type=str, nargs='+', choices=list(INSTRUCTION_TEMPLATES.keys()),
                        help='Add specific instruction templates to the outline prompt')
    parser.add_argument('--chapter-instructions', type=str, nargs='+', choices=list(INSTRUCTION_TEMPLATES.keys()),
                        help='Add specific instruction templates to the chapter prompts')
    parser.add_argument('--custom-instructions', type=str,
                        help='Add custom additional instructions for the outline prompt')
    
    # Add narrative style argument
    parser.add_argument('--narrative-style', type=str, default=NARRATIVE_STYLE,
                        choices=list(narrative_styles.keys()),
                        help='Narrative style to use throughout the book')
    
    # Add pedagogical approach argument
    parser.add_argument('--pedagogical-approach', type=str, default=PEDAGOGICAL_APPROACH,
                        choices=list(pedagogical_approaches.keys()),
                        help='Pedagogical approach to structure the content')
    
    # Add argument to list available styles and approaches
    parser.add_argument('--list-styles', action='store_true',
                        help='List all available narrative styles and exit')
    parser.add_argument('--list-approaches', action='store_true',
                        help='List all available pedagogical approaches and exit')
    
    args = parser.parse_args()
    
    # Handle listing available styles and approaches
    if args.list_styles:
        print("\nAvailable Narrative Styles:")
        print("---------------------------")
        for key, style in narrative_styles.items():
            print(f"{key}: {style['name']} - {style['description']}")
        sys.exit(0)
    
    if args.list_approaches:
        print("\nAvailable Pedagogical Approaches:")
        print("--------------------------------")
        for key, approach in pedagogical_approaches.items():
            print(f"{key}: {approach['name']} - {approach['description']}")
        sys.exit(0)
    
    # Determine which outline instructions to use
    outline_instructions = None
    if args.outline_instructions:
        # Use command-line specified template instructions for outline
        outline_instructions = args.outline_instructions
    elif args.custom_instructions:
        # Use command-line custom instructions directly
        outline_instructions = args.custom_instructions
    else:
        # Use the default SELECTED_OUTLINE_INSTRUCTIONS
        outline_instructions = SELECTED_OUTLINE_INSTRUCTIONS
    
    # Determine which chapter instructions to use
    chapter_instructions = args.chapter_instructions if args.chapter_instructions else SELECTED_CHAPTER_INSTRUCTIONS
    
    # Note: CUSTOM_INSTRUCTIONS will be added in generate_book_outline_prompt regardless
    
    create_minibook(
        args.topic, args.api_key, args.num_chapters, args.chapter_delay, 
        args.output_folder, not args.no_summary, outline_instructions, chapter_instructions,
        args.base_chapters, args.narrative_style, args.pedagogical_approach
    )

if __name__ == "__main__":
    main() 