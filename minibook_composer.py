import os
import re
import json
import shutil
import google.generativeai as genai
from datetime import datetime
import argparse
import time
from lib_prompts import PROMPTS

#Set your key, set your topic, go!

# Default values
DEFAULT_TOPIC = "An introduction to the FFT and DFT"
ADDITIONAL_INSTRUCTIONS = "This should be an introductory and practical guide for computer science students and ml engineers"
DEFAULT_API_KEY = os.environ.get('GOOGLE_API_KEY', 'AIzaSyCikXRo0qmngNr_L4ReLT3Vi4XPdpK2t2U')
DEFAULT_MODEL = 'gemini-1.5-pro'
DEFAULT_TEMPERATURE = 0.7
DEFAULT_TOP_P = 0.95

def setup_genai(api_key):
    """Initialize the Gemini API with the provided API key."""
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(DEFAULT_MODEL)

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
    project_path = f"{folder_name}_{timestamp}"
    
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
                    "temperature": DEFAULT_TEMPERATURE,
                    "top_p": DEFAULT_TOP_P,
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

def generate_book_outline_prompt(topic):
    """Generate the prompt for creating a book outline."""
    return PROMPTS["outline"].format(topic=topic)

def generate_book_outline(model, topic, project_path):
    """Generate a book outline for the given topic."""
    outline_prompt = generate_book_outline_prompt(topic)
    
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

def elaborate_chapter(model, chapter, project_path, index):
    """Generate detailed content for a chapter based on its outline."""
    chapter_title = chapter["title"]
    chapter_outline = chapter["outline"]
    
    prompt = PROMPTS["chapter_elaboration"].format(
        chapter_number=index+1,
        chapter_title=chapter_title,
        chapter_outline=chapter_outline
    )
    
    # Add a delay before each API call to avoid rate limiting
    print(f"Waiting 3 seconds before requesting content for Chapter {index+1}...")
    time.sleep(3)
    
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

def merge_chapters(chapters, topic, project_path):
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
    book_path = os.path.join(project_path, book_filename)
    
    # Save the complete book
    save_to_file(book_content, book_path)
    
    return book_path

def save_metadata(topic, project_path, chapters):
    """Save metadata about the project for future reference."""
    metadata = {
        "topic": topic,
        "created_at": datetime.now().isoformat(),
        "chapters": [{"title": chapter["title"], "file": os.path.basename(chapter["file"])} for chapter in chapters],
        "model": DEFAULT_MODEL,
        "temperature": DEFAULT_TEMPERATURE,
        "top_p": DEFAULT_TOP_P
    }
    
    metadata_path = os.path.join(project_path, "metadata.json")
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"Metadata saved to {metadata_path}")

def create_minibook(topic, api_key):
    """Main function to create a minibook on the given topic."""
    if not api_key:
        raise ValueError("Please provide a Google API key either as an argument or by setting the GOOGLE_API_KEY environment variable.")
    
    # Initialize Gemini model
    model = setup_genai(api_key)
    
    # Create project folder
    project_path = create_project_folder(topic)
    print(f"Created project folder: {project_path}")
    
    # Generate book outline
    print(f"Generating outline for: {topic}")
    outline = generate_book_outline(model, topic, project_path)
    
    # Parse chapters from outline
    chapters = parse_chapters(outline)
    print(f"Extracted {len(chapters)} chapters from outline")
    
    # Process each chapter
    processed_chapters = []
    for i, chapter in enumerate(chapters):
        print(f"Elaborating on Chapter {i+1}: {chapter['title']}")
        try:
            processed_chapter = elaborate_chapter(model, chapter, project_path, i)
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
    book_path = merge_chapters(processed_chapters, topic, project_path)
    
    # Save project metadata
    save_metadata(topic, project_path, processed_chapters)
    
    print(f"\nMinibook creation complete!")
    print(f"Project folder: {project_path}")
    print(f"Final book: {book_path}")
    
    return project_path, book_path

# For direct execution in IDE, uncomment and modify these lines:
# topic = "Introduction to Blockchain Technology"
# api_key = "your-api-key-here"  # Or use environment variable
# create_minibook(topic, api_key)

def main():
    parser = argparse.ArgumentParser(description='Create a minibook on a specified topic using AI.')
    parser.add_argument('--topic', type=str, default=DEFAULT_TOPIC, 
                        help=f'The topic for the minibook (default: "{DEFAULT_TOPIC}")')
    parser.add_argument('--api-key', type=str, default=DEFAULT_API_KEY,
                        help='Google API key (or set GOOGLE_API_KEY environment variable)')
    
    args = parser.parse_args()
    
    create_minibook(args.topic, args.api_key)

if __name__ == "__main__":
    main() 