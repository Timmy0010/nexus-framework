#!/usr/bin/env python
"""
Simple LLM Key Manager fallback that works without cryptography or keyring.
This provides basic functionality when secure dependencies aren't available.
"""

import os
import json
import warnings
from typing import Dict, Optional, Any

class BasicKeyManager:
    """
    A basic manager for LLM API keys that works without secure dependencies.
    Uses environment variables and plain JSON files only.
    """
    
    def __init__(self, keys_file: Optional[str] = "api_keys.json"):
        """
        Initialize the key manager.
        
        Args:
            keys_file: Optional path to a JSON file containing API keys
        """
        self.keys = {}
        self.keys_file = keys_file
        
        # Try to load keys from environment variables first
        self._load_keys_from_env()
        
        # Then try to load from file if it exists
        if keys_file and os.path.exists(keys_file):
            self._load_keys_from_file()
            
        # Print security warning
        warnings.warn(
            "Using basic key management without security features. "
            "This is not recommended for production use. "
            "Install cryptography and keyring packages for secure key management."
        )
    
    def _load_keys_from_env(self) -> None:
        """Load API keys from environment variables."""
        providers = ["google", "anthropic", "openai", "openrouter"]
        
        for provider in providers:
            possible_vars = [
                f"{provider.upper()}_API_KEY",
                f"{provider.upper()}_KEY",
                f"{provider}_api_key",
            ]
            
            for env_var in possible_vars:
                api_key = os.environ.get(env_var)
                if api_key:
                    self.keys[provider] = api_key
                    break
    
    def _load_keys_from_file(self) -> None:
        """Load API keys from a JSON file."""
        try:
            with open(self.keys_file, 'r') as f:
                keys_data = json.load(f)
                
            if isinstance(keys_data, dict):
                # Update only if keys aren't already set
                for provider, key in keys_data.items():
                    if provider not in self.keys and key:
                        self.keys[provider] = key
        except Exception as e:
            print(f"Warning: Error loading API keys from file: {e}")
    
    def get_api_key(self, provider: str) -> Optional[str]:
        """
        Get the API key for a specific provider.
        
        Args:
            provider: The provider name (e.g., 'google', 'anthropic')
            
        Returns:
            The API key if found, None otherwise
        """
        return self.keys.get(provider.lower())
    
    def set_api_key(self, provider: str, api_key: str) -> None:
        """
        Set the API key for a specific provider.
        
        Args:
            provider: The provider name
            api_key: The API key
        """
        self.keys[provider.lower()] = api_key
        
        # Save to file if available
        if self.keys_file:
            self._save_to_file()
    
    def _save_to_file(self) -> None:
        """Save the current API keys to the JSON file."""
        try:
            with open(self.keys_file, 'w') as f:
                json.dump(self.keys, f, indent=2)
                
            print(f"API keys saved to {self.keys_file}")
            print("NOTE: Storing keys in plaintext files is not secure.")
            print("Consider using environment variables or installing cryptography and keyring packages.")
        except Exception as e:
            print(f"Error saving API keys to file: {e}")
    
    def get_all_available_providers(self) -> list:
        """
        Get a list of all providers with available API keys.
        
        Returns:
            List of provider names with keys
        """
        return list(self.keys.keys())
    
    def interactive_setup(self) -> None:
        """Interactive setup to configure API keys (basic version)."""
        print("\n===== LLM API Key Setup (Basic Mode) =====")
        print("This will guide you through setting up API keys for LLM providers.")
        print("NOTE: This is using a basic setup without secure features.")
        print("For secure key storage, install: pip install cryptography keyring\n")
        
        providers = [
            ("google", "Google (Gemini models)"),
            ("anthropic", "Anthropic (Claude models)"), 
            ("openai", "OpenAI (GPT models)"),
            ("openrouter", "OpenRouter (Various models)")
        ]
        
        print("Select storage method:")
        print("1. Environment variables (recommended)")
        print("2. Plain JSON file (not secure for production)")
        
        try:
            choice = int(input("\nEnter choice (1-2): "))
            if choice < 1 or choice > 2:
                raise ValueError("Invalid choice")
                
            use_env = choice == 1
            
            for provider_key, provider_name in providers:
                print(f"\n--- {provider_name} ---")
                current_key = self.get_api_key(provider_key)
                
                if current_key:
                    masked_key = current_key[:4] + '*' * (len(current_key) - 8) + current_key[-4:]
                    print(f"Current key: {masked_key}")
                    update = input("Update this key? (y/n): ").lower() == 'y'
                else:
                    print("No key found.")
                    update = input("Add a key for this provider? (y/n): ").lower() == 'y'
                    
                if update:
                    api_key = input(f"Enter API key for {provider_name}: ")
                    if api_key:
                        self.keys[provider_key] = api_key
                        
                        if use_env:
                            env_var = f"{provider_key.upper()}_API_KEY"
                            if os.name == 'nt':  # Windows
                                print(f"To set this key permanently, run this command:")
                                print(f"[System.Environment]::SetEnvironmentVariable('{env_var}', '{api_key}', 'User')")
                            else:
                                print(f"To set this key permanently, add this line to your shell profile:")
                                print(f"export {env_var}='{api_key}'")
            
            # Save to file if chosen
            if not use_env:
                self._save_to_file()
                
            print("\nAPI key setup complete!")
            
        except (ValueError, IndexError) as e:
            print(f"Error: {e}. Setup aborted.")
        except KeyboardInterrupt:
            print("\nSetup cancelled.")
