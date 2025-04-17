# Gemini Question Answering Tool

A simple Python script that sends questions to Google's Gemini AI model and saves the responses as markdown files.

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

Run the script from the command line with arguments:

```bash
python gemini_qa.py --question "What is quantum computing?" --api-key "your-api-key-here"
```

The script includes default values, so you can run it without any arguments:

```bash
python gemini_qa.py
```

This will use the default question: "What are the benefits of artificial intelligence?"

### Running from IDE

For direct execution in an IDE, simply uncomment and modify these lines at the top of the script:

```python
# For direct execution in IDE, uncomment and modify these lines:
question = "What are the main challenges in quantum computing?"
api_key = "your-api-key-here"  # Or use environment variable
process_question(question, api_key)
```

## Output

The script will:
1. Send your question to the Gemini 1.5 Pro model
2. Generate a filename based on your question 
3. Save the response to a file
   
Example filename: `what_is_quantum_computing_20240520_123045.md` 