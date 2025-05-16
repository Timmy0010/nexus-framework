# Security Guidelines for Contributors

## Keeping API Keys Secure in Public Repositories

This project is hosted in a public repository. To ensure security of API keys and sensitive credentials, please follow these guidelines:

## Never Commit API Keys to the Repository

- **NEVER** commit any actual API keys, passwords, or sensitive information to the repository
- **NEVER** hardcode API keys, even temporarily for testing
- **ALWAYS** use the provided secure key management system

## Secure Development Practices

1. **Use Environment Variables for Development**
   - Set API keys as environment variables in your local development environment
   - Use tools like `python-dotenv` for local development, but don't commit the `.env` files

2. **Use the Secure Key Manager**
   - Use the `LLMKeyManager` class for accessing API keys
   - The manager provides several secure storage options

3. **Check the .gitignore**
   - Make sure sensitive files are properly included in `.gitignore`
   - Files that should never be committed:
     - `api_keys.json`
     - `*.encrypted`
     - `.env` files
     - Any file containing personal credentials

4. **Template Files Instead of Actual Configuration**
   - Use template files (e.g., `api_keys.template.json`) with placeholder values
   - Include instructions for users to create their own copy of these files

## Code Review Guidelines

When reviewing code, be vigilant about:

1. **Hardcoded Credentials**
   - Check for any hardcoded API keys or sensitive values
   - Look for strings that might be access tokens or API keys

2. **Insecure Storage**
   - Verify that sensitive information is properly encrypted or secured
   - Ensure credentials aren't stored in plaintext unnecessarily

3. **Logging Issues**
   - Make sure secrets aren't being logged
   - Watch for debug statements that might expose sensitive information

## Using the Secure Key Manager

The project includes a secure key manager that supports multiple storage methods:

1. **Environment Variables** (Most Secure)
   - Keys are stored in the system environment
   - Never saved to disk in the project directory

2. **System Keyring** (Secure)
   - Uses the operating system's secure credential store
   - Requires `keyring` package

3. **Encrypted File** (Moderately Secure)
   - Encrypts keys with a password
   - Requires `cryptography` package

4. **Plain JSON File** (Least Secure)
   - Only use for development in private environments
   - Never commit to version control

### Usage Example:

```python
from nexus_framework.llm_key_manager import LLMKeyManager

# Get an API key
key_manager = LLMKeyManager()
api_key = key_manager.get_api_key("google")

# Store an API key securely
key_manager.set_api_key("anthropic", "your-api-key", store_method="keyring")
```

## Security Dependencies

The secure key manager requires additional dependencies:

```bash
pip install cryptography keyring
```

For convenience, you can run `install_secure_deps.bat`.

## If You Find a Security Issue

If you discover any security vulnerabilities or exposed credentials:

1. **DO NOT** create a public GitHub issue
2. Contact the maintainers directly via email
3. If you discover committed credentials, notify the team immediately so they can be rotated

Remember: Security is everyone's responsibility. When in doubt, err on the side of caution.
