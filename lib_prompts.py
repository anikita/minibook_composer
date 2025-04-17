"""
Prompt templates for the minibook composer.

This file contains all the prompt templates used in the minibook generation process.
You can modify these prompts to fine-tune the AI's responses without changing the code logic.
"""

PROMPTS = {
    # Prompt to generate the book outline
    "outline": """
    Create a detailed outline for a minibook on "{topic}".
    The outline should:
    1. Include a title for the minibook
    2. Have 5-7 chapter titles. Number the chapters explicitly, starting from 1.
    3. For each chapter, provide 3-5 bullet points highlighting key concepts
    4. Add a chapter about history of the topic
    5. Add a chapter about the relation of the topic to other topics
    6. Format the output clearly with markdown

    The outline should be comprehensive but concise, covering the most important aspects of {topic}.
    """,
    
    # Prompt to elaborate on a specific chapter
    "chapter_elaboration": """
    Please write a detailed chapter section for a minibook on the following topic:
    
    Chapter Number: {chapter_number}
    Chapter Title: {chapter_title}
    
    Chapter Outline:
    {chapter_outline}
    
    IMPORTANT: Your response should begin with "## Chapter {chapter_number}: {chapter_title}" - don't use any other numbering scheme.
    
    Please elaborate on all the points in the outline, expanding with relevant examples, 
    explanations, and insights. Write in a clear, educational style appropriate for 
    a comprehensive minibook chapter. Format your response using markdown for headings, 
    lists, code blocks, etc. where appropriate.
    """
} 