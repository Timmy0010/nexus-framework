# Instructions for LLM Developers

## Overview

You are tasked with continuing development on the Nexus Framework, focusing on implementing the remaining components outlined in the Enhancement Roadmap. This document provides instructions on how to efficiently access the codebase and proceed with development.

## Getting Started

### 1. Generate Comprehensive Documentation

First, run the documentation generator script to create a consolidated view of the codebase:

```
generate_documentation.bat
```

This will produce a file named `nexus_framework_documentation.md` containing all relevant documentation, source code, and examples organized by category. Review this document thoroughly to understand the current state of the project.

### 2. Key Components to Implement

According to the Enhancement Roadmap, focus on these components in priority order:

1. **Complete Schema Validation (Phase 2.3)**
   - Build upon the partially implemented schema validation system
   - Implement error handling for invalid messages
   - Develop schema version migration strategy

2. **Complete Rate Limiting (Phase 4.3)**
   - Enhance the adaptive rate limiter
   - Implement dynamic adjustment based on service health
   - Develop monitoring capabilities

3. **VerificationAgent Implementation (Phase 3.1)**
   - Design and implement the verification agent architecture
   - Create plugin system for verification rules
   - Develop rule configuration and management

### 3. Development Guidelines

- Follow existing code patterns and style
- Maintain comprehensive docstrings and type hints
- Update the Enhancement Roadmap as components are completed
- Create appropriate examples for new components
- Add unit tests for all new functionality

### 4. File Structure

Use these key directories for implementation:

- `/nexus_framework/validation/` - For Schema Validation components
- `/nexus_framework/core/` - For Rate Limiting enhancements
- `/nexus_framework/security/` - For VerificationAgent implementation
- `/examples/` - For example implementations
- `/docs/` - For updated documentation

### 5. After Implementation

After implementing a component:

1. Update the Enhancement Roadmap to mark tasks as completed
2. Create or update relevant documentation
3. Develop example code demonstrating the new functionality
4. Regenerate the documentation using the script

## Reference

The consolidated documentation in `nexus_framework_documentation.md` contains all necessary information about:

- Project architecture and design patterns
- Existing component implementations
- Enhancement roadmap and priorities
- Integration points with other components
- Examples of similar implementations

Refer to this document as the primary source of information about the project.
