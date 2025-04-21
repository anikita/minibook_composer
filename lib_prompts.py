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
    - Include the scope of the minibook in the first chapter
    - Have at least {num_chapters} chapter titles. Number the chapters explicitly, starting from 1.
    - For each chapter, provide 4-6 bullet points highlighting key concepts.
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
    "key_takeaways": "Include in the first chapter the key takeaways of the topic, right after the introduction.",
    "summary_tables": "Try to use tables to summarize and compare key concepts.",
    "conclusion": "Add as a last chapter about the conclusion of the topic.",
    "formal_theories": "Add a chapter about the formal theories of the topic.",
    "key_terms": "Add a chapter about the key terms and definitions of the topic.",
    "interdisciplinary": "Add a chapter about the relation of the topic to other topics or disciplines/theories.",
    "future": "Add a chapter about future developments and trends in this field.",
    "applications": "Add a chapter about practical applications and real-world examples.",
    "controversies": "Add a chapter discussing controversies or debates within this field.",
    "key_figures": "Add a chapter about key figures and their contributions to this field.",
    "methodologies": "Add a chapter explaining research methodologies used in this field.",
    "case_studies": "Include relevant case studies throughout appropriate chapters.",
}

# Narrative Style options
NARRATIVE_STYLES = {
    "analogies": {
        "name": "Analogies",
        "description": "Use analogies and metaphors to explain complex concepts",
        "prompt": """
        Use analogies and metaphors throughout the book to make complex concepts more relatable. 
        Whenever introducing a new concept, try to relate it to something familiar from everyday life.
        """
    },
    "analogies_sports": {
        "name": "Sports Analogies",
        "description": "Use sports-related analogies to explain concepts",
        "prompt": """
        Use sports analogies and metaphors throughout the book to make complex concepts more relatable.
        Draw from sports like basketball, football, soccer, tennis, etc. to create relevant comparisons.
        """
    },
    "analogies_cooking": {
        "name": "Cooking Analogies",
        "description": "Use cooking-related analogies to explain concepts",
        "prompt": """
        Use cooking-related analogies and metaphors throughout the book to make complex concepts more relatable.
        Compare processes to recipes, ingredients, cooking techniques, etc.
        """
    },
    "analogies_business": {
        "name": "Business Analogies",
        "description": "Use business-related analogies to explain concepts",
        "prompt": """
        Use business and economics analogies throughout the book to make complex concepts more relatable.
        Draw from concepts like market forces, supply/demand, ROI, and business processes for comparisons.
        """
    },
    "character_driven": {
        "name": "Character-Driven",
        "description": "Use fictional or real characters to guide the reader",
        "prompt": """
        Structure the content as if guided by fictional or real characters who have expertise in the field.
        Introduce these characters early and use their perspectives to explain concepts throughout the book.
        Use phrases like "As Sarah, an experienced researcher in this field, would explain..." or create dialogue
        between characters to explain different viewpoints.
        """
    },
    "problem_solution": {
        "name": "Problem-Solution",
        "description": "Frame content as challenges with stepwise resolutions",
        "prompt": """
        Structure the content as a series of questions or challenges, followed by their answers or solutions.
        For each major concept, first frame it as a enquiry or challenge to be solved, then walk through the process of
        solving it step by step. Use this pattern consistently throughout the book.
        """
    },
    "challenge_solution": {
        "name": "Challenge-Solution",
        "description": "Frame content as specific challenges with detailed resolutions",
        "prompt": """
        Structure the content as a series of questions or challenges, followed by their answers or solutions.
        For each major concept, first frame it as a enquiry or challenge to be solved, then walk through the process of
        solving it step by step. 
        Follow the pattern: The Question (Challenge or Motivation) -> What we know (Evidence or Current Knowledge Status Quo) -> What we can do (Solution)
        You should  adapt the above pattern to the context at hand and use it throughout the book.
        For example in historical context it could be: The Question -> What was known -> What was done 
        """
    },
    "story_arc": {
        "name": "Story Arc",
        "description": "Use a classic narrative arc with beginning, middle, and end",
        "prompt": """
        Structure the entire book as a story with a clear beginning (introducing the challenge), 
        middle (exploring complications and attempts at solutions), and end (resolution and lessons learned).
        Include elements like a protagonist (which could be the reader), challenges, turning points, and resolution.
        """
    }
}

# Pedagogical Approach options
PEDAGOGICAL_APPROACHES = {
    "scaffolded": {
        "name": "Scaffolded Learning",
        "description": "Progressive disclosure of concepts, building on previous knowledge",
        "prompt": """
        Structure the content using a scaffolded approach, where each new concept builds upon previous ones.
        Start with fundamental concepts before moving to more complex ideas. Explicitly reference previous 
        concepts when introducing new ones to help the reader make connections.
        """
    },
    "socratic": {
        "name": "Socratic Method",
        "description": "Guide learning through questioning and critical thinking",
        "prompt": """
        Frame explanations as answers to questions the reader might have, and encourage the reader
        to question assumptions and explore different perspectives.
        Use the Socratic method throughout the book by posing thoughtful questions to the reader.
        """
    },
    "project_based": {
        "name": "Project-Based Learning",
        "description": "Structure content around a hands-on project or example",
        "prompt": """
        Structure the entire book around a practical project or example that progresses throughout the chapters.
        Start by introducing the project early, then develop it step by step across chapters, introducing new
        concepts as they become relevant to the project. By the end of the book, the reader should have
        completed the project or understood the example in depth.
        """
    },
    "spiral": {
        "name": "Spiral Learning",
        "description": "Revisit key ideas with increasing depth throughout the book",
        "prompt": """
        Use a spiral approach to learning, where core concepts are revisited multiple times with increasing depth.
        Introduce key ideas early in a simplified form, then circle back to them in later chapters to add complexity
        and nuance. Make explicit references to previous mentions when revisiting concepts.
        """
    }
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

def apply_style_and_approach(prompt, narrative_style=None, pedagogical_approach=None):
    """
    Apply selected narrative style and pedagogical approach to a prompt.
    
    Args:
        prompt (str): The base prompt to modify
        narrative_style (str): Key for the narrative style to apply
        pedagogical_approach (str): Key for the pedagogical approach to apply
        
    Returns:
        str: The modified prompt with style and approach instructions
    """
    modified_prompt = prompt
    
    # Apply narrative style if specified
    if narrative_style and narrative_style in NARRATIVE_STYLES:
        style_prompt = NARRATIVE_STYLES[narrative_style]["prompt"]
        modified_prompt += f"\n\nNarrative Style Instructions:\n{style_prompt}\n"
    
    # Apply pedagogical approach if specified
    if pedagogical_approach and pedagogical_approach in PEDAGOGICAL_APPROACHES:
        approach_prompt = PEDAGOGICAL_APPROACHES[pedagogical_approach]["prompt"]
        modified_prompt += f"\n\nPedagogical Approach Instructions:\n{approach_prompt}\n"
    
    return modified_prompt

def get_available_styles():
    """Returns a dictionary of available narrative styles with names and descriptions."""
    return {k: {"name": v["name"], "description": v["description"]} for k, v in NARRATIVE_STYLES.items()}

def get_available_approaches():
    """Returns a dictionary of available pedagogical approaches with names and descriptions."""
    return {k: {"name": v["name"], "description": v["description"]} for k, v in PEDAGOGICAL_APPROACHES.items()} 