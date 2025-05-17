#!/usr/bin/env python3
"""
Nexus Framework Documentation Concatenator

This script concatenates all relevant documentation, source code, and example files
that an LLM would need to continue development on the Nexus Framework project.
It produces a single markdown file with all the content organized by category.
"""

import os
import glob
import datetime

# Configuration
PROJECT_ROOT = r"C:\Users\thohn\ConformProcess\nexus_agent_project"
OUTPUT_FILE = os.path.join(PROJECT_ROOT, "nexus_framework_documentation.md")

# File categories and their paths (relative to PROJECT_ROOT)
FILE_CATEGORIES = {
    "Project Documentation": [
        "README.md",
        "docs/ENHANCEMENT_ROADMAP.md",
        "docs/ACCESS_CONTROL_SYSTEM.md",
        "CONTRIBUTING.md",
        "SECURITY.md",
        "MCP_INTEGRATION_README.md",
        "QUICK_START_MCP.md",
    ],
    "Core Framework": [
        "nexus_framework/__init__.py",
        "nexus_framework/core/*.py",
    ],
    "Security Components": [
        "nexus_framework/security/__init__.py",
        "nexus_framework/security/authentication/__init__.py",
        "nexus_framework/security/authentication/auth_service.py",
        "nexus_framework/security/authentication/auth_middleware.py",
        "nexus_framework/security/authentication/bus_integration.py",
        "nexus_framework/security/access_control/__init__.py",
        "nexus_framework/security/access_control/permissions.py",
        "nexus_framework/security/access_control/roles.py",
        "nexus_framework/security/access_control/policies.py",
        "nexus_framework/security/access_control/acl.py",
        "nexus_framework/security/access_control/middleware.py",
        "nexus_framework/security/access_control/integration.py",
    ],
    "Communication and Messaging": [
        "nexus_framework/communication/*.py",
        "nexus_framework/messaging/*.py",
    ],
    "Validation and Schema": [
        "nexus_framework/validation/*.py",
    ],
    "Rate Limiting and Resilience": [
        "nexus_framework/core/rate_limiter.py",
    ],
    "Examples": [
        "examples/access_control_example.py",
        "examples/reliable_team_example.py",
    ],
}

def read_file_content(file_path):
    """Read and return the content of a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"

def get_file_extension(file_path):
    """Get the file extension."""
    _, ext = os.path.splitext(file_path)
    return ext.lower()

def format_file_content(file_path, content):
    """Format the file content based on file type."""
    ext = get_file_extension(file_path)
    rel_path = os.path.relpath(file_path, PROJECT_ROOT)
    
    # Format the output with file path as header and appropriate code fencing
    if ext in ['.py', '.json', '.yml', '.yaml']:
        language = 'python' if ext == '.py' else 'json' if ext == '.json' else 'yaml'
        return f"## {rel_path}\n\n```{language}\n{content}\n```\n\n"
    elif ext in ['.md', '.txt']:
        # For markdown files, we include the content directly but under a heading
        return f"## {rel_path}\n\n{content}\n\n"
    else:
        # For other files, use plain code fencing
        return f"## {rel_path}\n\n```\n{content}\n```\n\n"

def main():
    """Main function to concatenate files."""
    # Create output file with header
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as out_file:
        # Write header
        out_file.write(f"# Nexus Framework Complete Documentation\n\n")
        out_file.write(f"*Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
        out_file.write("This document contains all relevant documentation, source code, and examples ")
        out_file.write("for continuing development on the Nexus Framework project.\n\n")
        out_file.write("## Table of Contents\n\n")
        
        # Generate table of contents
        for category in FILE_CATEGORIES:
            out_file.write(f"- [{category}](#{category.lower().replace(' ', '-')})\n")
        out_file.write("\n---\n\n")
        
        # Process each category and files
        for category, file_patterns in FILE_CATEGORIES.items():
            out_file.write(f"# {category}\n\n")
            
            # Process all files matching the patterns in this category
            for pattern in file_patterns:
                full_pattern = os.path.join(PROJECT_ROOT, pattern)
                matching_files = glob.glob(full_pattern)
                
                for file_path in matching_files:
                    if os.path.isfile(file_path):
                        content = read_file_content(file_path)
                        formatted_content = format_file_content(file_path, content)
                        out_file.write(formatted_content)
    
    print(f"Documentation generated successfully: {OUTPUT_FILE}")
    print(f"Total categories: {len(FILE_CATEGORIES)}")
    
    # Count total files processed
    total_files = 0
    for category, file_patterns in FILE_CATEGORIES.items():
        for pattern in file_patterns:
            full_pattern = os.path.join(PROJECT_ROOT, pattern)
            matching_files = glob.glob(full_pattern)
            total_files += len([f for f in matching_files if os.path.isfile(f)])
    
    print(f"Total files processed: {total_files}")

if __name__ == "__main__":
    main()
