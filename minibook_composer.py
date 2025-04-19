import os
import re
import json
import shutil
import google.generativeai as genai
from datetime import datetime
import argparse
import time
from lib_prompts import PROMPTS, get_outline_prompt, INSTRUCTION_TEMPLATES, get_instruction_templates

# Import user-specific configuration if available
try:
    from config import API_KEY, OUTPUT_FOLDER, PROJECT_FOLDER, MODEL, TEMPERATURE, TOP_P
    print("Using configuration from config.py")
except ImportError:
    print("Config file not found. Using default configuration.")
    # Default configuration if config.py is not available
    API_KEY = os.environ.get('GOOGLE_API_KEY', '')
    OUTPUT_FOLDER = os.path.join(os.path.expanduser("~"), "Documents/Minibooks")
    PROJECT_FOLDER = "MyBooks"
    MODEL = 'gemini-2.5-flash-preview-04-17'
    TEMPERATURE = 0.7
    TOP_P = 0.95

# Build your own minibook
# Set your key, set your topic, go!

# User parameters
TOPIC = "Storytelling in Science Education, a practical guide"

# Default instruction templates to use when none are provided by command line
SELECTED_INSTRUCTIONS = [ "key_terms","history", "future", ] # e.g ["history", "future"]

# Add additional instructions for the AI here
ADDITIONAL_INSTRUCTIONS = """
-Explain different strategies and options around narrative structure
-Make it a practical guide for advanced scientist and engineers to communicate complex concepts to non-technical audiences
"""

NUM_CHAPTERS = 'dynamic'  # Can be a number or 'dynamic' to calculate based on instructions
BASE_CHAPTER_COUNT = 3    # Base number of chapters when using dynamic mode
CHAPTER_DELAY = 1  # Default wait time in seconds between chapter requests

def setup_genai(api_key):
    """Initialize the Gemini API with the provided API key."""
    genai.configure(api_key=api_key)
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
    if additional_instructions:
        # If it's a string, use it directly
        if isinstance(additional_instructions, str):
            if additional_instructions.strip():
                # Format nicely with newlines
                formatted_instructions = "\n\nAdditional instructions:\n" + additional_instructions
                outline_prompt += formatted_instructions
        
        # If it's a list of keys from INSTRUCTION_TEMPLATES
        elif isinstance(additional_instructions, list):
            if additional_instructions:
                instructions_text = []
                for key in additional_instructions:
                    if key in INSTRUCTION_TEMPLATES:
                        instructions_text.append("- " + INSTRUCTION_TEMPLATES[key])
                
                if instructions_text:
                    formatted_instructions = "\n\nAdditional instructions:\n" + "\n".join(instructions_text)
                    outline_prompt += formatted_instructions
    
    # Format the final prompt with topic and num_chapters
    return outline_prompt.format(topic=topic, num_chapters=actual_num_chapters)

def generate_book_outline(model, topic, project_path, num_chapters, additional_instructions=None, base_chapters=BASE_CHAPTER_COUNT):
    """Generate a book outline for the given topic."""
    outline_prompt = generate_book_outline_prompt(topic, num_chapters, additional_instructions, base_chapters)
    
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

def elaborate_chapter(model, chapter, project_path, index, delay=CHAPTER_DELAY):
    """Generate detailed content for a chapter based on its outline."""
    chapter_title = chapter["title"]
    chapter_outline = chapter["outline"]
    
    prompt = PROMPTS["chapter_elaboration"].format(
        chapter_number=index+1,
        chapter_title=chapter_title,
        chapter_outline=chapter_outline
    )
    
    # Add a delay before each API call to avoid rate limiting
    if delay > 0:
        print(f"Waiting {delay} seconds before requesting content for Chapter {index+1}...")
        time.sleep(delay)
    
    chapter_content = ask_gemini(model, prompt)
    
    # Create chapter filename
    safe_chapter_title = sanitize_filename(chapter_title)
    chapter_filename = f"chapter_{index+1}_{safe_chapter_title}.md"
    chapter_path = os.path.join(project_path, "chapters", chapter_filename)
    
    # Save chapter content
    save_to_file(chapter_content, chapter_path)
    
    return {
        "title": chapter_title,
        "content": chapter_content,
        "file": chapter_path
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

def save_metadata(topic, project_path, chapters, outline_prompt=None, additional_instructions=None, num_chapters=None):
    """Save metadata about the project for future reference."""
    metadata = {
        "topic": topic,
        "created_at": datetime.now().isoformat(),
        "chapters": [{"title": chapter["title"], "file": os.path.basename(chapter["file"])} for chapter in chapters],
        "model": MODEL,
        "temperature": TEMPERATURE,
        "top_p": TOP_P,
        "settings": {
            "num_chapters": num_chapters or NUM_CHAPTERS,
            "chapter_delay": CHAPTER_DELAY
        }
    }
    
    # Include additional_instructions if available
    if additional_instructions:
        if isinstance(additional_instructions, list):
            # Convert list of template keys to their actual instructions
            instructions_text = []
            for key in additional_instructions:
                if key in INSTRUCTION_TEMPLATES:
                    instructions_text.append(INSTRUCTION_TEMPLATES[key])
            metadata["additional_instructions"] = instructions_text
        else:
            # String instructions
            metadata["additional_instructions"] = additional_instructions
    
    # Include the outline prompt if available
    if outline_prompt:
        metadata["outline_prompt"] = outline_prompt
    
    metadata_path = os.path.join(project_path, "metadata.json")
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"Metadata saved to {metadata_path}")

def create_minibook(topic, api_key, num_chapters, chapter_delay=CHAPTER_DELAY, 
                    output_folder=OUTPUT_FOLDER, add_summary=True, additional_instructions=None, base_chapters=BASE_CHAPTER_COUNT):
    """Main function to create a minibook on the given topic."""
    if not api_key:
        raise ValueError("Please provide a Google API key either as an argument or by setting the GOOGLE_API_KEY environment variable.")
    
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
    model = setup_genai(api_key)
    
    # Create project folder
    project_path = create_project_folder(topic)
    print(f"Created project folder: {project_path}")
    
    # Generate book outline
    print(f"Generating outline for: {topic}")
    outline_prompt = generate_book_outline_prompt(topic, actual_num_chapters, additional_instructions, base_chapters)
    outline = generate_book_outline(model, topic, project_path, actual_num_chapters, additional_instructions, base_chapters)
    
    # Parse chapters from outline
    chapters = parse_chapters(outline)
    print(f"Extracted {len(chapters)} chapters from outline")
    
    # Process each chapter
    processed_chapters = []
    for i, chapter in enumerate(chapters):
        print(f"Elaborating on Chapter {i+1}: {chapter['title']}")
        try:
            processed_chapter = elaborate_chapter(model, chapter, project_path, i, chapter_delay)
            processed_chapters.append(processed_chapter)
        except Exception as e:
            print(f"Error processing chapter {i+1}: {str(e)}")
            # Create a placeholder for the failed chapter
            safe_chapter_title = sanitize_filename(chapter["title"])
            chapter_filename = f"chapter_{i+1}_{safe_chapter_title}.md"
            chapter_path = os.path.join(project_path, "chapters", chapter_filename)
            error_content = f"# {chapter['title']}\n\nError generating content: {str(e)}\n\nOutline:\n{chapter['outline']}"
            save_to_file(error_content, chapter_path)
            processed_chapters.append({
                "title": chapter["title"],
                "content": error_content,
                "file": chapter_path
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
    save_metadata(topic, project_path, processed_chapters, outline_prompt, additional_instructions, actual_num_chapters)
    
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
    parser = argparse.ArgumentParser(description='Create a minibook on a specified topic using AI.')
    parser.add_argument('--topic', type=str, default=TOPIC, 
                        help=f'The topic for the minibook (default: "{TOPIC}")')
    parser.add_argument('--api-key', type=str, default=API_KEY,
                        help='Google API key (or set GOOGLE_API_KEY environment variable)')
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
    parser.add_argument('--add-instructions', type=str, nargs='+', choices=list(INSTRUCTION_TEMPLATES.keys()),
                        help='Add specific instruction templates to the outline prompt')
    parser.add_argument('--custom-instructions', type=str,
                        help='Add custom additional instructions for the outline prompt')
    
    args = parser.parse_args()
    
    # Determine which additional instructions to use
    additional_instructions = None
    if args.add_instructions:
        additional_instructions = args.add_instructions
    elif args.custom_instructions:
        additional_instructions = args.custom_instructions
    else:
        # Use SELECTED_INSTRUCTIONS first if it's not empty, otherwise use ADDITIONAL_INSTRUCTIONS
        additional_instructions = SELECTED_INSTRUCTIONS if SELECTED_INSTRUCTIONS else ADDITIONAL_INSTRUCTIONS
    
    create_minibook(args.topic, args.api_key, args.num_chapters, args.chapter_delay, 
                    args.output_folder, not args.no_summary, additional_instructions, args.base_chapters)

if __name__ == "__main__":
    main() 