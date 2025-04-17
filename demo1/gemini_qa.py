import os
import re
import google.generativeai as genai
from datetime import datetime
import argparse

# Default values
DEFAULT_QUESTION = "What are the benefits of artificial intelligence?"
DEFAULT_API_KEY = os.environ.get('GOOGLE_API_KEY', 'AIzaSyCikXRo0qmngNr_L4ReLT3Vi4XPdpK2t2U')
DEFAULT_MODEL = 'gemini-1.5-pro'
DEFAULT_TEMPERATURE = 0.7
DEFAULT_TOP_P = 0.95

def setup_genai(api_key):
    """Initialize the Gemini API with the provided API key."""
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(DEFAULT_MODEL)

def generate_filename(question, max_length=50):
    """Generate a filename from the question."""
    # Remove special characters and replace spaces with underscores
    sanitized = re.sub(r'[^a-zA-Z0-9 ]', '', question)
    words = sanitized.split()
    
    # Take first few words to create a concise filename
    if len(words) > 5:
        words = words[:5]
    
    filename = "_".join(words).lower()
    
    # Truncate if too long
    if len(filename) > max_length:
        filename = filename[:max_length]
        
    # Add timestamp to ensure uniqueness
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{filename}_{timestamp}.md"

def ask_gemini(model, question):
    """Send a question to Gemini and get the response."""
    response = model.generate_content(
        question,
        generation_config={
            "temperature": DEFAULT_TEMPERATURE,
            "top_p": DEFAULT_TOP_P,
            "response_mime_type": "text/plain",
        }
    )
    return response.text

def save_to_markdown(content, filename):
    """Save the content to a markdown file."""
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Response saved to {filename}")

def process_question(question=DEFAULT_QUESTION, api_key=DEFAULT_API_KEY):
    """Main function to process a question and save the response."""
    if not api_key:
        raise ValueError("Please provide a Google API key either as an argument or by setting the GOOGLE_API_KEY environment variable.")
    
    # Initialize Gemini model
    model = setup_genai(api_key)
    
    # Generate response
    response = ask_gemini(model, question)
    
    # Create filename and save response
    filename = generate_filename(question)
    save_to_markdown(response, filename)
    
    return filename

# For direct execution in IDE, uncomment and modify these lines:
# question = "What are the main challenges in quantum computing?"
# api_key = "your-api-key-here"  # Or use environment variable
# process_question(question, api_key)

def main():
    parser = argparse.ArgumentParser(description='Ask Gemini a question and save the response as markdown.')
    parser.add_argument('--question', type=str, default=DEFAULT_QUESTION, 
                        help=f'The question to ask Gemini (default: "{DEFAULT_QUESTION}")')
    parser.add_argument('--api-key', type=str, default=DEFAULT_API_KEY,
                        help='Google API key (or set GOOGLE_API_KEY environment variable)')
    
    args = parser.parse_args()
    
    process_question(args.question, args.api_key)

if __name__ == "__main__":
    main() 