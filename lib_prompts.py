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
    - Include a title for the minibook
    - Have {num_chapters} chapter titles. Number the chapters explicitly, starting from 1.
    - For each chapter, provide 4-6 bullet points highlighting key concepts.
    - Last chapter should be a conclusion with key takeaways.
    - Use a tables where needed to summarize and compare.
    - Format the output clearly with markdown. Use latex for formulas.

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

# Additional instruction templates that can be combined with base prompts
INSTRUCTION_TEMPLATES = {
    "history": "Add a chapter about the history of the topic.",
    "key_terms": "Add a chapter about the key terms and definitions of the topic.",
    "interdisciplinary": "Add a chapter about the relation of the topic to other topics or disciplines/theories.",
    "future": "Add a chapter about future developments and trends in this field.",
    "applications": "Add a chapter about practical applications and real-world examples.",
    "controversies": "Add a chapter discussing controversies or debates within this field.",
    "key_figures": "Add a chapter about key figures and their contributions to this field.",
    "methodologies": "Add a chapter explaining research methodologies used in this field.",
    "case_studies": "Include relevant case studies throughout appropriate chapters."
}

def get_outline_prompt():
    """
    Returns the outline prompt template.
    This function allows for more flexible manipulation of the prompt template.
    """
    return PROMPTS["outline"]

def get_instruction_templates():
    """
    Returns the instruction templates dictionary.
    This function allows for more flexible access to instruction templates.
    """
    return INSTRUCTION_TEMPLATES 