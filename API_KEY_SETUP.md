# API Key Setup for Nexus Framework

This document explains how to set up and configure API keys for different LLM providers in the Nexus Framework.

## Available LLM Providers

The Nexus Framework supports the following LLM providers:

1. **Google** (Gemini models)
2. **Anthropic** (Claude models)
3. **OpenAI** (GPT models)
4. **OpenRouter** (Various models from different providers)

## API Key Configuration Methods

There are two ways to configure your API keys:

### 1. Environment Variables

You can set environment variables for your API keys:

```bash
# For Windows PowerShell
$env:GOOGLE_API_KEY="your-google-api-key"
$env:ANTHROPIC_API_KEY="your-anthropic-api-key"
$env:OPENAI_API_KEY="your-openai-api-key"
$env:OPENROUTER_API_KEY="your-openrouter-api-key"

# For Windows Command Prompt
set GOOGLE_API_KEY=your-google-api-key
set ANTHROPIC_API_KEY=your-anthropic-api-key
set OPENAI_API_KEY=your-openai-api-key
set OPENROUTER_API_KEY=your-openrouter-api-key

# For Linux/Mac
export GOOGLE_API_KEY="your-google-api-key"
export ANTHROPIC_API_KEY="your-anthropic-api-key"
export OPENAI_API_KEY="your-openai-api-key"
export OPENROUTER_API_KEY="your-openrouter-api-key"
```

### 2. JSON Configuration File

Alternatively, you can create a JSON file named `api_keys.json` in your project directory:

```json
{
  "google": "your-google-api-key",
  "anthropic": "your-anthropic-api-key",
  "openai": "your-openai-api-key",
  "openrouter": "your-openrouter-api-key"
}
```

## Obtaining API Keys

### Google API Key
1. Go to [Google AI Studio](https://makersuite.google.com/)
2. Sign in with your Google account
3. Go to "API Keys" in the settings
4. Create a new API key for the Gemini models

### Anthropic API Key
1. Go to [Anthropic Console](https://console.anthropic.com/)
2. Sign in or create an account
3. Navigate to the API Keys section
4. Create a new API key

### OpenAI API Key
1. Go to [OpenAI Platform](https://platform.openai.com/)
2. Sign in or create an account
3. Navigate to the API Keys section
4. Create a new API key

### OpenRouter API Key
1. Go to [OpenRouter](https://openrouter.ai/)
2. Sign in or create an account
3. Go to your account dashboard
4. Generate a new API key

## Verifying Your API Keys

You can verify your API keys by running the `llm_key_manager.py` script:

```bash
python nexus_framework/llm_key_manager.py google
```

Replace `google` with the provider you want to check.

## Troubleshooting

If you encounter issues with API keys:

1. Ensure your API key is valid and not expired
2. Check that you have sufficient credits or quota for the service
3. Verify that the API key has the correct permissions
4. Make sure your environment variables are set correctly
5. Confirm that your `api_keys.json` file is properly formatted

## Security Considerations

- Never commit your API keys to version control
- Consider using environment variables for production environments
- Regularly rotate your API keys for better security
- Use the minimum necessary permissions for your API keys
