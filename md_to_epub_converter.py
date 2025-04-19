#!/usr/bin/env python3
"""
Markdown to EPUB Converter

This script scans a directory for markdown files and converts them to EPUB format.
It requires pandoc to be installed on your system.
"""

import os
import argparse
import subprocess
import sys
from pathlib import Path
import shutil
import tempfile
import re

# Import user-specific configuration if available
try:
    from config import MD_TO_EPUB_INPUT_DIR, MD_TO_EPUB_OUTPUT_DIR
    DEFAULT_INPUT_DIR = MD_TO_EPUB_INPUT_DIR
    DEFAULT_OUTPUT_DIR = MD_TO_EPUB_OUTPUT_DIR
    print("Using directories from config.py")
except ImportError:
    print("Config file not found. Using default directories.")
    # Default configuration if config.py is not available
    DEFAULT_INPUT_DIR = os.path.join(os.path.expanduser("~"), "Documents/Minibooks")
    DEFAULT_OUTPUT_DIR = DEFAULT_INPUT_DIR

def check_pandoc_installed():
    """Check if pandoc is installed on the system."""
    try:
        result = subprocess.run(['pandoc', '--version'], 
                               stdout=subprocess.PIPE, 
                               stderr=subprocess.PIPE, 
                               text=True, 
                               check=False)
        return result.returncode == 0
    except FileNotFoundError:
        return False

def preprocess_markdown(input_file, output_file=None):
    """
    Preprocess markdown file to fix common formatting issues with bullet points.
    
    Args:
        input_file (str): Path to the input markdown file
        output_file (str, optional): Path to save the preprocessed file. If None, 
                                     a temporary file will be created.
    
    Returns:
        str: Path to the preprocessed file
    """
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # First, protect bold/italic markers by replacing them temporarily
    # Find patterns like *word* or **word** that are used for emphasis, not bullets
    content = re.sub(r'(?<!\*)\*\*(?!\s)(.+?)(?<!\s)\*\*(?!\*)', r'__DOUBLE_STAR__\1__DOUBLE_STAR__', content)
    content = re.sub(r'(?<!\*)\*(?!\s|\*)(.+?)(?<!\s|\*)\*(?!\*)', r'__SINGLE_STAR__\1__SINGLE_STAR__', content)
    
    # Now fix bullet points that don't have proper line breaks
    # Only match asterisks at the beginning of lines or after a newline with optional spaces
    content = re.sub(r'(^|\n)(\s*)\*\s+([^\n]+)(\s*)\n(\s*)\*\s+', r'\1\2* \3\4\n\5* ', content)
    
    # Fix bullet points that don't have spaces after the asterisk
    # Only match asterisks at the beginning of lines or after a newline with optional spaces
    content = re.sub(r'(^|\n)(\s*)\*([^\s\*])', r'\1\2* \3', content)
    
    # Ensure there's a line break before bullet points that follow normal text
    # But avoid adding too many line breaks - one is sufficient
    content = re.sub(r'([^\n])\n(\s*\*\s+)', r'\1\n\n\2', content)
    
    # Make sure there's proper spacing between bullet points and non-bullet text
    # Add only one newline, not two
    content = re.sub(r'(^|\n)(\s*\*\s+[^\n]+)\n([^\*\s])', r'\1\2\n\3', content)
    
    # Make sure consecutive bullet points are properly spaced (just one newline)
    content = re.sub(r'(^|\n)(\s*\*\s+[^\n]+)\n\n(\s*\*\s+)', r'\1\2\n\3', content)
    
    # Restore bold/italic markers
    content = content.replace('__DOUBLE_STAR__', '**')
    content = content.replace('__SINGLE_STAR__', '*')
    
    # Create a temporary file if output_file is not specified
    if not output_file:
        fd, output_file = tempfile.mkstemp(suffix='.md')
        os.close(fd)
    
    # Write the preprocessed content
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return output_file

def convert_md_to_epub(md_file, output_dir=DEFAULT_OUTPUT_DIR, title=None):
    """
    Convert a markdown file to EPUB format using pandoc.
    
    Args:
        md_file (str): Path to the markdown file
        output_dir (str, optional): Directory to save the EPUB file. If None, save in same directory.
        title (str, optional): Title for the EPUB. If None, use the filename without extension.
        
    Returns:
        str: Path to the generated EPUB file, or None if conversion failed
    """
    if not os.path.exists(md_file):
        print(f"Error: File {md_file} does not exist.")
        return None
    
    # Get base filename without extension
    base_name = os.path.basename(md_file)
    file_name_without_ext = os.path.splitext(base_name)[0]
    
    # If no title specified, use the filename
    if not title:
        title = file_name_without_ext.replace('_', ' ').title()
    
    # Determine output path
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{file_name_without_ext}.epub")
    else:
        output_path = os.path.join(os.path.dirname(md_file), f"{file_name_without_ext}.epub")
        
    # Preprocess the markdown file to fix formatting issues
    preprocessed_file = None
    css_file = None
    
    try:
        # Preprocess the markdown file
        preprocessed_file = preprocess_markdown(md_file)
        print(f"Preprocessed markdown file created: {preprocessed_file}")
        
        # Create a temporary CSS file for styling
        css_content = """
        body {
            font-family: serif;
            margin: 5%;
            text-align: justify;
        }
        h1, h2, h3, h4, h5, h6 {
            font-family: sans-serif;
            margin-top: 2em;
        }
        /* Fix for bullet points */
        ul {
            display: block;
            list-style-type: disc;
            margin-top: 1em;
            margin-bottom: 1em;
            padding-left: 40px;
        }
        li {
            display: list-item;
            margin-bottom: 0.5em;
            padding-left: 5px;
        }
        ol {
            display: block;
            list-style-type: decimal;
            margin-top: 1em;
            margin-bottom: 1em;
            padding-left: 40px;
        }
        /* Additional list styling for better compatibility */
        ul li:before {
            content: "";
            margin-right: 0;
        }
        """
        
        # Create a temporary CSS file
        fd, css_file = tempfile.mkstemp(suffix='.css')
        with os.fdopen(fd, 'w') as f:
            f.write(css_content)
        
        # Build the pandoc command with CSS styling - use the preprocessed file
        cmd = [
            'pandoc',
            preprocessed_file,  # Use preprocessed file instead of original
            '-o', output_path,
            '--metadata', f'title={title}',
            '--epub-cover-image=cover.png' if os.path.exists('cover.png') else None,
            '--toc',  # Add table of contents
            '--standalone',
            '--css', css_file,  # Apply our custom CSS
            '--wrap=none',  # Prevent pandoc from rewrapping text
            '--markdown-headings=atx'  # Use # style headings consistently
        ]
        
        # Remove None values
        cmd = [c for c in cmd if c is not None]
        
        # Run pandoc
        print(f"Converting {md_file} to EPUB...")
        result = subprocess.run(cmd, 
                              stdout=subprocess.PIPE, 
                              stderr=subprocess.PIPE, 
                              text=True, 
                              check=False)
        
        if result.returncode == 0:
            print(f"Successfully created: {output_path}")
            return output_path
        else:
            print(f"Error converting {md_file}:")
            print(result.stderr)
            return None
    except Exception as e:
        print(f"Exception occurred: {e}")
        return None
    finally:
        # Clean up the temporary files
        if preprocessed_file and os.path.exists(preprocessed_file):
            os.remove(preprocessed_file)
        if css_file and os.path.exists(css_file):
            os.remove(css_file)

def scan_and_convert(input_dir, output_dir=None, recursive=False):
    """
    Scan a directory for markdown files and convert them to EPUB.
    
    Args:
        input_dir (str): Directory to scan for markdown files
        output_dir (str, optional): Directory to save EPUB files
        recursive (bool): Whether to scan subdirectories
        
    Returns:
        int: Number of successfully converted files
    """
    if not os.path.isdir(input_dir):
        print(f"Error: {input_dir} is not a valid directory.")
        return 0
    
    # Get all markdown files in the directory
    if recursive:
        md_files = []
        for root, _, files in os.walk(input_dir):
            for file in files:
                if file.lower().endswith('.md'):
                    md_files.append(os.path.join(root, file))
    else:
        md_files = [os.path.join(input_dir, f) for f in os.listdir(input_dir) 
                   if f.lower().endswith('.md') and os.path.isfile(os.path.join(input_dir, f))]
    
    if not md_files:
        print(f"No markdown files found in {input_dir}.")
        return 0
    
    print(f"Found {len(md_files)} markdown files.")
    
    # Convert each file
    success_count = 0
    for md_file in md_files:
        if convert_md_to_epub(md_file, output_dir):
            success_count += 1
    
    return success_count

def main():
    parser = argparse.ArgumentParser(description='Convert markdown files to EPUB format.')
    parser.add_argument('input_dir', nargs='?', default=DEFAULT_INPUT_DIR,
                        help=f'Directory containing markdown files (default: {DEFAULT_INPUT_DIR})')
    parser.add_argument('--output-dir', '-o', default=DEFAULT_OUTPUT_DIR,
                        help=f'Directory to save EPUB files (default: {DEFAULT_OUTPUT_DIR})')
    parser.add_argument('--recursive', '-r', action='store_true', 
                        help='Recursively scan subdirectories')
    parser.add_argument('--single-file', '-s', 
                        help='Convert a single markdown file instead of scanning a directory')
    parser.add_argument('--title', '-t', help='Title for the EPUB (only used with --single-file)')
    
    args = parser.parse_args()
    
    # Check if pandoc is installed
    if not check_pandoc_installed():
        print("Error: pandoc is not installed or not in the system PATH.")
        print("Please install pandoc (https://pandoc.org/installing.html) and try again.")
        sys.exit(1)
    
    # Convert a single file if specified
    if args.single_file:
        epub_path = convert_md_to_epub(args.single_file, args.output_dir, args.title)
        if epub_path:
            print(f"Conversion complete: {epub_path}")
            sys.exit(0)
        else:
            print("Conversion failed.")
            sys.exit(1)
    
    # Otherwise, scan directory and convert all markdown files
    success_count = scan_and_convert(args.input_dir, args.output_dir, args.recursive)
    
    print(f"\nConversion complete. Successfully converted {success_count} files.")
    
if __name__ == "__main__":
    main() 