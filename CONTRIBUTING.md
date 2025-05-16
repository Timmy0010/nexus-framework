# Contributing to Nexus Framework

First of all, thank you for considering contributing to the Nexus Framework! This project aims to create a powerful, flexible framework for building AI agent systems, and we need the help of the community to make it the best it can be.

This document provides guidelines and instructions for contributing to the Nexus Framework. By participating in this project, you agree to abide by its terms.

## Code of Conduct

We want to foster an inclusive and respectful community around the Nexus Framework. Please be respectful and constructive in your communications with other contributors and maintainers.

## Getting Started

1. **Fork the repository** on GitHub.
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/yourusername/nexus-framework.git
   cd nexus-framework
   ```
3. **Set up the development environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -e ".[dev]"
   ```
4. **Create a branch** for your changes:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Development Process

### Before You Start

1. **Check existing issues** to see if your problem or idea has already been addressed.
2. **Create an issue** to discuss major changes before putting significant effort into them.
3. **Look at the project board** to understand current priorities and work in progress.

### Making Changes

1. **Follow the coding style** of the project (PEP 8 for Python code).
2. **Add or update tests** to cover your changes.
3. **Add or update documentation** as necessary.
4. **Make sure all tests pass** locally before submitting a pull request.

### Commit Messages

Follow these guidelines for commit messages:

- Use the present tense ("Add feature" not "Added feature")
- Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit the first line to 72 characters or less
- Reference issues and pull requests liberally after the first line
- Consider starting the commit message with an applicable emoji:
  - 🎨 `:art:` when improving the format/structure of the code
  - 🐛 `:bug:` when fixing a bug
  - 📝 `:memo:` when adding or updating documentation
  - ✨ `:sparkles:` when adding a new feature
  - 🔧 `:wrench:` when dealing with configuration
  - 🚀 `:rocket:` when improving performance
  - 🧪 `:test_tube:` when adding tests

### Pull Requests

1. **Update your fork** to the latest upstream changes before submitting a pull request.
2. **Create a pull request** from your feature branch to the main repository.
3. **Include a clear description** of the changes made and any relevant issue numbers.
4. **Make sure CI passes** for your pull request.
5. **Be responsive to feedback** and be willing to make changes to your pull request if requested.

## Testing

Run tests locally with pytest:

```bash
pytest
```

For coverage reports:

```bash
pytest --cov=nexus_framework
```

## Coding Standards

### Python

- Follow [PEP 8](https://pep8.org/) for all Python code.
- Use type hints wherever possible.
- Write docstrings for all public classes, methods, and functions.
- Keep functions small and focused on a single responsibility.

### Documentation

- Use Markdown for documentation files.
- Add code examples for non-obvious features.
- Keep the API documentation up to date with code changes.

## Project Structure

```
nexus_framework/
├── core/           # Core abstractions and data structures
├── agents/         # Specialized agent implementations
├── communication/  # Communication components
├── tools/          # Tool integration
├── orchestration/  # Multi-agent orchestration
├── security/       # Security components
└── observability/  # Logging, monitoring, and tracing

tests/              # Test suite
docs/               # Documentation
examples/           # Example scripts
```

## Feature Requests

We welcome feature requests! Please create an issue in the GitHub repository and:

1. Clearly describe the feature you would like to see.
2. Explain why it would be valuable to the project.
3. Discuss possible implementations or approaches.

## Bug Reports

When reporting bugs, please include:

1. A clear description of the bug.
2. Steps to reproduce the issue.
3. Expected behavior vs. actual behavior.
4. Any relevant logs or error messages.
5. Your operating system and Python version.
6. If possible, a minimal code example that demonstrates the issue.

## Code Review Process

All submissions require review before being merged:

1. Maintainers will review your code for quality, correctness, and adherence to the project's style.
2. You may be asked to make changes to your submission.
3. Once approved, a maintainer will merge your changes.

## Becoming a Maintainer

Active contributors may be invited to become maintainers. Maintainers have write access to the repository and help review pull requests, triage issues, and guide the project's direction.

## License

By contributing to the Nexus Framework, you agree that your contributions will be licensed under the project's MIT License.

## Questions

If you have any questions about contributing, please create an issue labeled "question" in the GitHub repository.

Thank you for contributing to the Nexus Framework!
