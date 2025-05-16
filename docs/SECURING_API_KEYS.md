# Securing API Keys in a Public Repository

## Overview

This guide explains how to securely manage API keys and other sensitive credentials when working with the Nexus Framework in a public GitHub repository.

## Security Risks

When working with a public repository:

1. **Exposure of Credentials**: Any API keys committed to the repository become publicly accessible
2. **Unauthorized Usage**: Exposed API keys can lead to unauthorized API usage and unexpected charges
3. **Account Compromise**: Some keys could potentially grant access to your accounts
4. **Data Breaches**: Keys might allow access to sensitive data

## Secure Key Management Methods

The Nexus Framework offers multiple methods for securely managing API keys:

### 1. Environment Variables (Recommended for Production)

**Advantages**:
- Nothing stored in project files
- Not committed to version control
- Isolated from application code

**Setup**:
```bash
# Set environment variables
export GOOGLE_API_KEY="your-key-here"
export ANTHROPIC_API_KEY="your-key-here"
export OPENAI_API_KEY="your-key-here"
```

For permanent setup on Windows:
```powershell
[System.Environment]::SetEnvironmentVariable('GOOGLE_API_KEY', 'your-key-here', 'User')
```

### 2. System Keyring (Recommended for Development)

**Advantages**:
- Uses OS-level secure credential storage
- Not stored in project files
- Easy to use during development

**Setup**:
```bash
# Run the interactive setup and select "System keyring" option
python secure_key_setup.bat
```

**Usage**:
```python
from nexus_framework.llm_key_manager import LLMKeyManager
key_manager = LLMKeyManager()
api_key = key_manager.get_api_key("google")
```

### 3. Encrypted File (Alternative)

**Advantages**:
- Can be committed to version control (if properly encrypted)
- Requires password to decrypt
- More convenient than manual environment variable setup

**Setup**:
```bash
# Run the interactive setup and select "Encrypted file" option
python secure_key_setup.bat
```

### 4. Plain JSON (NOT Recommended for Public Repositories)

This method stores keys in a plain text JSON file. It should **NEVER** be used in a public repository unless you're absolutely certain the file is in your `.gitignore`.

## Security Best Practices

1. **Use .gitignore**: 
   - Make sure `api_keys.json` and other sensitive files are in `.gitignore`
   - The project already includes these settings

2. **Regular Key Rotation**:
   - Periodically change your API keys
   - Especially important if you suspect any exposure

3. **Minimal Permissions**:
   - Create keys with the minimal permissions needed
   - Use restricted API keys when possible

4. **Monitoring**:
   - Monitor usage of your API keys
   - Set up alerts for unusual activity

5. **Template Files**:
   - Use `api_keys.template.json` with placeholder values
   - Actual key files should never be committed

## What to Do If You Accidentally Commit API Keys

If you accidentally commit API keys to a public repository:

1. **Revoke the Keys Immediately**:
   - Go to the provider's website and revoke/regenerate the exposed keys
   - This is the most important step, as removing them from Git history isn't enough

2. **Remove from Git History**:
   - Use tools like BFG Repo-Cleaner or git-filter-branch
   - Force push the changes

3. **Notify Relevant Parties**:
   - Let team members know about the exposure
   - If organizational keys, follow your organization's security incident procedures

## Setting Up Your Keys

The easiest way to set up your API keys securely is to use the included setup wizard:

```bash
# Run the interactive setup
secure_key_setup.bat
```

This wizard will guide you through selecting a storage method and entering your API keys.

## Checking Your Configuration

To check which providers have API keys configured:

```bash
python -m nexus_framework.llm_key_manager
```

To check a specific provider:

```bash
python -m nexus_framework.llm_key_manager google
```

## Additional Resources

- [GitHub Secret Scanning](https://docs.github.com/en/github/administering-a-repository/about-secret-scanning)
- [Git-secrets](https://github.com/awslabs/git-secrets)
- [Pre-commit hooks](https://pre-commit.com/)
