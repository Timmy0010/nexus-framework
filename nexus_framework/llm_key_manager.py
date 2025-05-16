#!/usr/bin/env python
"""
Enhanced LLM Key Manager that securely loads API keys from environment variables or encrypted files.
"""

import os
import json
import sys
import warnings
from typing import Dict, Optional, Any

# Try to import secure dependencies
try:
    import base64
    import getpass
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    import keyring
    import platform
    SECURE_FEATURES = True
except ImportError:
    SECURE_FEATURES = False
    warnings.warn(
        "Secure key management dependencies not available. "
        "Install with: pip install cryptography keyring"
    )
    # Import basic key manager as fallback
    try:
        from nexus_framework.basic_key_manager import BasicKeyManager
    except ImportError:
        # If that fails too, define it inline
        class BasicKeyManager:
            def __init__(self, keys_file=None):
                self.keys = {}
                self._load_keys_from_env()
                if keys_file and os.path.exists(keys_file):
                    self._load_keys_from_file(keys_file)
                
            def _load_keys_from_env(self):
                for p in ["google", "anthropic", "openai", "openrouter"]:
                    key = os.environ.get(f"{p.upper()}_API_KEY")
                    if key:
                        self.keys[p] = key
                        
            def _load_keys_from_file(self, path):
                try:
                    with open(path, 'r') as f:
                        data = json.load(f)
                    for p, key in data.items():
                        if p not in self.keys and key:
                            self.keys[p] = key
                except Exception as e:
                    print(f"Error loading keys: {e}")
                    
            def get_api_key(self, provider):
                return self.keys.get(provider.lower())
                
            def get_all_available_providers(self):
                return list(self.keys.keys())
                
            def interactive_setup(self):
                print("Secure key setup not available. Install dependencies.")
                
            def set_api_key(self, provider, api_key):
                self.keys[provider.lower()] = api_key

class LLMKeyManager:
    """
    A secure manager for LLM API keys that supports multiple storage methods:
    1. Environment variables (most secure)
    2. System keyring (secure)
    3. Encrypted file (moderately secure)
    4. Plain JSON file (least secure, but convenient for development)
    """
    
    def __init__(self, keys_file: Optional[str] = "api_keys.json"):
        """
        Initialize the key manager.
        
        Args:
            keys_file: Optional path to a JSON file containing API keys
        """
        self.keys = {}
        self.keys_file = keys_file
        self.system_name = "NexusFramework"
        
        # Try loading keys in order of security preference
        self._load_keys_from_env()
        
        if not self.keys:
            self._load_keys_from_keyring()
            
        if not self.keys and keys_file:
            # Try to load from encrypted file first
            encrypted_file = f"{os.path.splitext(keys_file)[0]}.encrypted"
            if os.path.exists(encrypted_file):
                self._load_keys_from_encrypted_file(encrypted_file)
            # Fall back to plain JSON if no encrypted file or failed to decrypt
            elif os.path.exists(keys_file):
                self._load_keys_from_file()
    
    def _load_keys_from_env(self) -> None:
        """Load API keys from environment variables (most secure method)."""
        providers = ["google", "anthropic", "openai", "openrouter"]
        
        for provider in providers:
            # Check multiple possible environment variable naming patterns
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
    
    def _load_keys_from_keyring(self) -> None:
        """Load API keys from the system's secure keyring."""
        try:
            providers = ["google", "anthropic", "openai", "openrouter"]
            
            for provider in providers:
                try:
                    key = keyring.get_password(self.system_name, f"{provider}_api_key")
                    if key:
                        self.keys[provider] = key
                except Exception:
                    # Skip if keyring access fails for this provider
                    pass
        except Exception as e:
            print(f"Warning: Could not access system keyring: {e}")
    
    def _load_keys_from_file(self) -> None:
        """Load API keys from a plain JSON file (least secure, but convenient)."""
        try:
            with open(self.keys_file, 'r') as f:
                keys_data = json.load(f)
                
            if isinstance(keys_data, dict):
                # Update only if keys aren't already set
                for provider, key in keys_data.items():
                    if provider not in self.keys and key:  # Only add non-empty keys
                        self.keys[provider] = key
        except Exception as e:
            print(f"Warning: Error loading API keys from file: {e}")
    
    def _load_keys_from_encrypted_file(self, encrypted_file: str) -> None:
        """Load API keys from an encrypted file."""
        try:
            # Only prompt for password if the file exists
            if os.path.exists(encrypted_file):
                password = self._get_password("Enter passphrase to decrypt API keys: ")
                key = self._derive_key(password)
                
                with open(encrypted_file, 'rb') as f:
                    encrypted_data = f.read()
                
                fernet = Fernet(key)
                decrypted_data = fernet.decrypt(encrypted_data)
                keys_data = json.loads(decrypted_data.decode())
                
                # Update only if keys aren't already set
                for provider, key in keys_data.items():
                    if provider not in self.keys and key:
                        self.keys[provider] = key
        except Exception as e:
            print(f"Warning: Could not decrypt API keys file: {e}")
    
    def _derive_key(self, password: str, salt: bytes = None) -> bytes:
        """Derive an encryption key from a password."""
        if salt is None:
            # Use a fixed salt - while not ideal for security, it allows 
            # decryption with just the password
            salt = b'NexusFrameworkSalt'
            
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key
    
    def _get_password(self, prompt: str) -> str:
        """Get a password from the user, handling different environments."""
        try:
            # Try to use getpass for secure password input
            return getpass.getpass(prompt)
        except Exception:
            # Fall back to regular input if getpass fails
            return input(prompt)
    
    def get_api_key(self, provider: str) -> Optional[str]:
        """
        Get the API key for a specific provider.
        
        Args:
            provider: The provider name (e.g., 'google', 'anthropic')
            
        Returns:
            The API key if found, None otherwise
        """
        return self.keys.get(provider.lower())
    
    def set_api_key(self, provider: str, api_key: str, store_method: str = "keyring") -> None:
        """
        Set the API key for a specific provider and store it securely.
        
        Args:
            provider: The provider name
            api_key: The API key
            store_method: Where to store the key: "env", "keyring", "encrypted", or "file"
        """
        provider = provider.lower()
        self.keys[provider] = api_key
        
        if store_method == "env":
            # Just print instructions for setting environment variable
            env_var = f"{provider.upper()}_API_KEY"
            if platform.system() == "Windows":
                print(f"To set this key permanently, run this command:")
                print(f"[System.Environment]::SetEnvironmentVariable('{env_var}', '{api_key}', 'User')")
            else:
                print(f"To set this key permanently, add this line to your shell profile:")
                print(f"export {env_var}='{api_key}'")
                
        elif store_method == "keyring":
            try:
                keyring.set_password(self.system_name, f"{provider}_api_key", api_key)
                print(f"API key for {provider} stored in system keyring")
            except Exception as e:
                print(f"Error storing key in keyring: {e}")
                self._save_to_file(provider, api_key)
                
        elif store_method == "encrypted":
            try:
                self._save_to_encrypted_file()
            except Exception as e:
                print(f"Error encrypting key: {e}")
                self._save_to_file(provider, api_key)
                
        elif store_method == "file":
            self._save_to_file(provider, api_key)
            
        else:
            print(f"Unknown storage method: {store_method}. Key stored in memory only.")
    
    def _save_to_file(self, provider: str = None, api_key: str = None) -> None:
        """Save the current API keys (or a specific key) to the JSON file."""
        if not self.keys_file:
            print("No keys file specified. Cannot save.")
            return
            
        try:
            # Load existing keys if the file exists
            existing_keys = {}
            if os.path.exists(self.keys_file):
                with open(self.keys_file, 'r') as f:
                    existing_keys = json.load(f)
            
            # Update with the new key if provided, otherwise use all keys
            if provider and api_key:
                existing_keys[provider] = api_key
            else:
                existing_keys.update(self.keys)
                
            # Write back to file
            with open(self.keys_file, 'w') as f:
                json.dump(existing_keys, f, indent=2)
                
            print(f"API keys saved to {self.keys_file}")
            print("NOTE: Storing keys in plaintext files is not secure. Consider using environment variables instead.")
        except Exception as e:
            print(f"Error saving API keys to file: {e}")
    
    def _save_to_encrypted_file(self) -> None:
        """Save all API keys to an encrypted file."""
        if not self.keys_file:
            print("No keys file specified. Cannot save encrypted file.")
            return
            
        try:
            # Prompt for a password
            password = self._get_password("Enter passphrase to encrypt API keys: ")
            confirm = self._get_password("Confirm passphrase: ")
            
            if password != confirm:
                print("Passphrases do not match. Keys not encrypted.")
                return
                
            key = self._derive_key(password)
            encrypted_file = f"{os.path.splitext(self.keys_file)[0]}.encrypted"
            
            # Encrypt the keys data
            keys_json = json.dumps(self.keys).encode()
            fernet = Fernet(key)
            encrypted_data = fernet.encrypt(keys_json)
            
            # Write to file
            with open(encrypted_file, 'wb') as f:
                f.write(encrypted_data)
                
            print(f"API keys encrypted and saved to {encrypted_file}")
        except Exception as e:
            print(f"Error encrypting API keys: {e}")
    
    def get_all_available_providers(self) -> list:
        """
        Get a list of all providers with available API keys.
        
        Returns:
            List of provider names with keys
        """
        return list(self.keys.keys())
    
    def interactive_setup(self) -> None:
        """Interactive setup to configure API keys securely."""
        print("\n===== LLM API Key Setup =====")
        print("This will guide you through setting up API keys for LLM providers.")
        print("Choose your preferred storage method for maximum security.\n")
        
        providers = [
            ("google", "Google (Gemini models)"),
            ("anthropic", "Anthropic (Claude models)"), 
            ("openai", "OpenAI (GPT models)"),
            ("openrouter", "OpenRouter (Various models)")
        ]
        
        print("Select storage method:")
        print("1. Environment variables (most secure, persistent across sessions)")
        print("2. System keyring (secure, easier to use)")
        print("3. Encrypted file (moderately secure)")
        print("4. Plain JSON file (least secure, convenient for development)")
        
        try:
            choice = int(input("\nEnter choice (1-4): "))
            if choice < 1 or choice > 4:
                raise ValueError("Invalid choice")
                
            methods = ["env", "keyring", "encrypted", "file"]
            selected_method = methods[choice - 1]
            
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
                    api_key = getpass.getpass(f"Enter API key for {provider_name}: ")
                    if api_key:
                        self.set_api_key(provider_key, api_key, selected_method)
                        
            print("\nAPI key setup complete!")
            
        except (ValueError, IndexError) as e:
            print(f"Error: {e}. Setup aborted.")
        except KeyboardInterrupt:
            print("\nSetup cancelled.")

# Command-line interface for testing and setup
if __name__ == "__main__":
    import sys
    
    manager = LLMKeyManager()
    
    # Check if we're running in setup mode
    if len(sys.argv) == 2 and sys.argv[1] == "setup":
        manager.interactive_setup()
        sys.exit(0)
        
    # Otherwise, check for a provider argument
    if len(sys.argv) == 2:
        provider = sys.argv[1]
        api_key = manager.get_api_key(provider)
        
        if api_key:
            masked_key = api_key[:4] + '*' * (len(api_key) - 8) + api_key[-4:] if len(api_key) > 8 else "********"
            print(f"API key for {provider}: {masked_key}")
        else:
            print(f"No API key found for {provider}")
            print("To set up API keys securely, run: python llm_key_manager.py setup")
    else:
        # List all available providers
        providers = manager.get_all_available_providers()
        if providers:
            print("Available providers with API keys:")
            for provider in providers:
                print(f"- {provider}")
        else:
            print("No API keys configured.")
            print("To set up API keys securely, run: python llm_key_manager.py setup")
