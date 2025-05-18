#!/usr/bin/env python
"""
Script to find all documentation files (.md and .txt) and example files
from the project folder, concatenate them, and output a new markdown file.
"""

import os
import glob
from pathlib import Path

def main():
    """
    Main function to find and concatenate documentation and example files.
    """
    # Set the project root directory
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    # Output file path
    output_file = os.path.join(project_root, "project_documentation.md")
    
    # Lists to store file paths
    doc_files = []
    example_files = []
    
    # Find all .md files in the project directory and subdirectories
    md_files = glob.glob(os.path.join(project_root, "**/*.md"), recursive=True)
    doc_files.extend(md_files)
    
    # Find all .txt files in the project directory and subdirectories
    txt_files = glob.glob(os.path.join(project_root, "**/*.txt"), recursive=True)
    doc_files.extend(txt_files)
    
    # Find all .py files in the examples directory and subdirectories
    example_py_files = glob.glob(os.path.join(project_root, "examples/**/*.py"), recursive=True)
    example_files.extend(example_py_files)
    
    # Sort files for consistent output
    doc_files.sort()
    example_files.sort()
    
    # Check if files were found
    if not doc_files and not example_files:
        print("No documentation or example files found.")
        return
    
    # Dictionary for tracking processed files to avoid duplicates
    processed_files = set()
    
    # Open output file for writing
    with open(output_file, "w", encoding="utf-8") as outfile:
        outfile.write("# Nexus Agent Project Documentation\n\n")
        outfile.write("This file contains concatenated documentation and example files.\n\n")
        
        # Process documentation files
        outfile.write("## Documentation Files\n\n")
        for file_path in doc_files:
            # Skip the output file itself if it exists and got included
            if os.path.abspath(file_path) == os.path.abspath(output_file):
                continue
                
            # Skip already processed files
            if file_path in processed_files:
                continue
                
            processed_files.add(file_path)
            
            # Get relative path for display
            rel_path = os.path.relpath(file_path, project_root)
            
            try:
                with open(file_path, "r", encoding="utf-8") as infile:
                    content = infile.read()
                    
                outfile.write(f"### File: {rel_path}\n\n")
                outfile.write(f"```{os.path.splitext(file_path)[1][1:]}  # File extension as language\n")
                outfile.write(content)
                outfile.write("\n```\n\n")
                print(f"Added: {rel_path}")
            except Exception as e:
                print(f"Error processing {rel_path}: {e}")
        
        # Process example files
        outfile.write("## Example Files\n\n")
        for file_path in example_files:
            # Skip already processed files
            if file_path in processed_files:
                continue
                
            processed_files.add(file_path)
            
            # Get relative path for display
            rel_path = os.path.relpath(file_path, project_root)
            
            try:
                with open(file_path, "r", encoding="utf-8") as infile:
                    content = infile.read()
                    
                outfile.write(f"### File: {rel_path}\n\n")
                outfile.write("```python\n")  # Python syntax highlighting
                outfile.write(content)
                outfile.write("\n```\n\n")
                print(f"Added: {rel_path}")
            except Exception as e:
                print(f"Error processing {rel_path}: {e}")
    
    print(f"\nAll files have been concatenated into: {output_file}")
    print(f"Total documentation files: {len(doc_files)}")
    print(f"Total example files: {len(example_files)}")

if __name__ == "__main__":
    main()
