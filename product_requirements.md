# Minibook Composer - Product Requirements Document

## Overview

Minibook Composer is a Python-based application that leverages AI to automatically generate comprehensive minibooks on any topic. The tool creates structured, well-organized content with minimal user input, saving both intermediate outputs and the final compiled book in markdown format.

## Target Users

- Content creators seeking to quickly generate educational material
- Researchers needing to compile information on specific topics
- Educators creating learning materials
- Writers looking for structured outlines for further development
- Students compiling research on particular subjects

## Key Features

### 1. AI-Powered Content Generation

- **Requirement**: Generate complete minibooks from a single topic prompt
- **Priority**: High
- **Description**: The application should leverage Google's Gemini AI to generate comprehensive, structured content based on a user-provided topic.

### 2. Structured Book Creation

- **Requirement**: Create logically structured books with chapters, sections, and a table of contents
- **Priority**: High
- **Description**: Each generated book should follow a consistent format with a title, table of contents, chapters, and subsections.

### 3. Customizable Output

- **Requirement**: Allow users to customize the number of chapters and other parameters
- **Priority**: Medium
- **Description**: Users should be able to specify the desired number of chapters, add additional instructions, and customize other aspects of the generated content.

### 4. Project Organization

- **Requirement**: Create organized project folders for each book topic
- **Priority**: Medium
- **Description**: Each generated book should be saved in its own project folder with a clear structure including intermediate outputs and the final compiled book.

### 5. Content Persistence

- **Requirement**: Save all intermediate steps and outputs
- **Priority**: Medium
- **Description**: The application should save the book outline, individual chapter content, and the final compiled book in separate files for review and further editing.

### 6. Command-Line Interface

- **Requirement**: Provide a simple command-line interface for operation
- **Priority**: High
- **Description**: Users should be able to run the application from the command line with parameters such as topic, API key, and number of chapters.

## Technical Requirements

### 1. External Dependencies

- **Requirement**: Utilize Google's Gemini AI API
- **Priority**: High
- **Description**: The application requires a Google API key to access Gemini's capabilities for content generation.

### 2. Performance

- **Requirement**: Handle API rate limiting and implement retry mechanisms
- **Priority**: Medium
- **Description**: The application should gracefully handle API rate limits with exponential backoff and retry mechanisms.

### 3. Extensibility

- **Requirement**: Allow for prompt customization without code changes
- **Priority**: Medium
- **Description**: All AI prompts should be stored in a centralized file for easy customization without modifying the main application code.

### 4. Output Format

- **Requirement**: Generate content in markdown format
- **Priority**: High
- **Description**: All generated content should be in markdown format to ensure compatibility with various platforms and tools.

## User Interface

### 1. Command-Line Arguments

- **Requirement**: Support command-line arguments for customization
- **Priority**: High
- **Description**: The application should accept command-line arguments for:
  - Topic (--topic)
  - API key (--api-key)
  - Number of chapters (--num-chapters)
  - Project folder location

### 2. Configuration

- **Requirement**: Support configuration through environment variables
- **Priority**: Medium
- **Description**: Users should be able to configure the application through environment variables (e.g., GOOGLE_API_KEY) for convenience.

## Output Structure

### 1. Project Folder

- **Requirement**: Create a structured project folder for each book
- **Priority**: High
- **Description**: Each project folder should include:
  - outline.md: The initial book outline
  - metadata.json: Project metadata
  - minibook_[topic].md: The final compiled book
  - chapters/: Directory containing individual chapter content

## Future Enhancements

### 1. GUI Interface

- **Requirement**: Provide a graphical user interface
- **Priority**: Low
- **Description**: Future versions could include a GUI for users who prefer not to use the command line.

### 2. Export Formats

- **Requirement**: Support additional export formats (PDF, EPUB, etc.)
- **Priority**: Low
- **Description**: Future versions could include the ability to export the generated content in various formats beyond markdown.

### 3. Template System

- **Requirement**: Support various book templates and styles
- **Priority**: Low
- **Description**: Future versions could include different templates for various types of books or content needs.

## Constraints

- Requires Python 3.7 or higher
- Depends on external API service (Google Gemini)
- Subject to API rate limits and quotas
- Generated content quality depends on the AI model's capabilities 