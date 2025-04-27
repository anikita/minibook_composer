#!/usr/bin/env python3
"""
Minibook Scanner

This script scans the PROJECT_FOLDER for folders starting with '+', 
finds markdown files following the 'minibook_*.md' pattern inside them,
and copies these files to OUTPUT_FOLDER with the 'minibook_' prefix removed.
"""

import os
import shutil
import glob
from config import PROJECT_FOLDER, OUTPUT_FOLDER

def scan_and_copy_minibooks():
    """
    Scan for minibooks and copy them to the output directory.
    """
    # Ensure output folder exists
    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)
        print(f"Created output directory: {OUTPUT_FOLDER}")
    
    # Get the full path to the project folder
    # This assumes PROJECT_FOLDER is just a folder name, not a full path
    # We'll create it in the same directory as the script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_path = os.path.join(script_dir, PROJECT_FOLDER)
    
    print(f"Scanning for minibooks in: {project_path}")
    
    # Counter for tracking found and copied files
    found_count = 0
    copied_count = 0
    
    # Check if project folder exists
    if not os.path.exists(project_path):
        print(f"Project folder not found: {project_path}")
        return
    
    # Find all folders starting with '+' in the project folder
    plus_folders = [f for f in os.listdir(project_path) 
                    if os.path.isdir(os.path.join(project_path, f)) and f.startswith('+')]
    
    print(f"Found {len(plus_folders)} folders starting with '+'")
    
    for folder in plus_folders:
        folder_path = os.path.join(project_path, folder)
        
        # Find all minibook_*.md files in this folder
        minibook_pattern = os.path.join(folder_path, "minibook_*.md")
        minibook_files = glob.glob(minibook_pattern)
        
        found_count += len(minibook_files)
        
        for minibook in minibook_files:
            # Get the filename without the path
            file_name = os.path.basename(minibook)
            
            # Remove the "minibook_" prefix and add '* ' prefix
            new_name = "+ " + file_name.replace("minibook_", "", 1)
            
            # Create the destination path
            destination = os.path.join(OUTPUT_FOLDER, new_name)
            
            # Copy the file
            shutil.copy2(minibook, destination)
            copied_count += 1
            
            print(f"Copied: {file_name} -> {new_name}")
    
    print(f"\nSummary:")
    print(f"- Scanned {len(plus_folders)} folders starting with '+'")
    print(f"- Found {found_count} minibook markdown files")
    print(f"- Copied {copied_count} files to {OUTPUT_FOLDER}")

if __name__ == "__main__":
    scan_and_copy_minibooks() 