#!/usr/bin/env python
import os
import json
import requests
from typing import Dict, List, Any, Optional, Union
import sys
import time

# Import LLM Key Manager
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from llm_key_manager import LLMKeyManager

class ModelProvider:
    """Base class for model providers."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        
    def generate(self, 
                 prompt: str, 
                 model_id: str, 
                 temperature: float = 0.7, 
                 max_tokens: int = 1000,
                 system_prompt: Optional[str] = None) -> str:
        """Generate text from the model."""
        raise NotImplementedError("Subclasses must implement this method")
        
    def is_multimodal(self, model_id: str) -> bool:
        """Check if model supports multimodal inputs."""
        raise NotImplementedError("Subclasses must implement this method")

class GoogleProvider(ModelProvider):
    """Provider for Google's Gemini models."""
    
    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.base_url = "https://generativelanguage.googleapis.com/v1/models"
        self.multimodal_models = ["gemini-pro-vision"]
        
    def generate(self, 
                 prompt: str, 
                 model_id: str = "gemini-pro", 
                 temperature: float = 0.7, 
                 max_tokens: int = 1000,
                 system_prompt: Optional[str] = None) -> str:
        """Generate text using Google's Gemini models."""
        url = f"{self.base_url}/{model_id}:generateContent?key={self.api_key}"
        
        # Build the request payload
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens
            }
        }
        
        # Add system prompt if provided
        if system_prompt:
            payload["contents"].insert(0, {"parts": [{"text": system_prompt}], "role": "system"})
            
        # Send the request
        response = requests.post(url, json=payload)
        
        if response.status_code != 200:
            print(f"Error calling Gemini API: {response.status_code} {response.text}")
            return f"Error: {response.text}"
            
        result = response.json()
        
        # Extract the generated text
        try:
            generated_text = result["candidates"][0]["content"]["parts"][0]["text"]
            return generated_text
        except (KeyError, IndexError) as e:
            print(f"Error parsing Gemini response: {e}")
            return f"Error parsing response: {str(e)}"
    
    def is_multimodal(self, model_id: str) -> bool:
        """Check if model is multimodal."""
        return model_id in self.multimodal_models

class AnthropicProvider(ModelProvider):
    """Provider for Anthropic's Claude models."""
    
    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.base_url = "https://api.anthropic.com/v1/messages"
        self.multimodal_models = [
            "claude-3-opus-20240229", 
            "claude-3-5-sonnet-20240620", 
            "claude-3-haiku-20240307"
        ]
        
    def generate(self, 
                 prompt: str, 
                 model_id: str = "claude-3-haiku-20240307", 
                 temperature: float = 0.7, 
                 max_tokens: int = 1000,
                 system_prompt: Optional[str] = None) -> str:
        """Generate text using Anthropic's Claude models."""
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01"
        }
        
        payload = {
            "model": model_id,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        # Add system prompt if provided
        if system_prompt:
            payload["system"] = system_prompt
            
        # Send the request
        response = requests.post(self.base_url, headers=headers, json=payload)
        
        if response.status_code != 200:
            print(f"Error calling Anthropic API: {response.status_code} {response.text}")
            return f"Error: {response.text}"
            
        result = response.json()
        
        # Extract the generated text
        try:
            generated_text = result["content"][0]["text"]
            return generated_text
        except (KeyError, IndexError) as e:
            print(f"Error parsing Anthropic response: {e}")
            return f"Error parsing response: {str(e)}"
    
    def is_multimodal(self, model_id: str) -> bool:
        """Check if model is multimodal."""
        return any(model_id.startswith(model) for model in self.multimodal_models)

class OpenAIProvider(ModelProvider):
    """Provider for OpenAI's models."""
    
    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.base_url = "https://api.openai.com/v1/chat/completions"
        self.multimodal_models = ["gpt-4-vision-preview", "gpt-4o"]
        
    def generate(self, 
                 prompt: str, 
                 model_id: str = "gpt-4o", 
                 temperature: float = 0.7, 
                 max_tokens: int = 1000,
                 system_prompt: Optional[str] = None) -> str:
        """Generate text using OpenAI's models."""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        messages = []
        
        # Add system prompt if provided
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
            
        # Add user prompt
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": model_id,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        # Send the request
        response = requests.post(self.base_url, headers=headers, json=payload)
        
        if response.status_code != 200:
            print(f"Error calling OpenAI API: {response.status_code} {response.text}")
            return f"Error: {response.text}"
            
        result = response.json()
        
        # Extract the generated text
        try:
            generated_text = result["choices"][0]["message"]["content"]
            return generated_text
        except (KeyError, IndexError) as e:
            print(f"Error parsing OpenAI response: {e}")
            return f"Error parsing response: {str(e)}"
    
    def is_multimodal(self, model_id: str) -> bool:
        """Check if model is multimodal."""
        return model_id in self.multimodal_models

class OpenRouterProvider(ModelProvider):
    """Provider for OpenRouter's models."""
    
    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        # OpenRouter has many multimodal models, these are just a few
        self.multimodal_models = [
            "anthropic/claude-3-opus", 
            "anthropic/claude-3-sonnet", 
            "google/gemini-pro-vision",
            "openai/gpt-4o"
        ]
        
    def generate(self, 
                 prompt: str, 
                 model_id: str = "openai/gpt-4o", 
                 temperature: float = 0.7, 
                 max_tokens: int = 1000,
                 system_prompt: Optional[str] = None) -> str:
        """Generate text using OpenRouter's models."""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://nexus-framework.org"  # Replace with your actual domain
        }
        
        messages = []
        
        # Add system prompt if provided
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
            
        # Add user prompt
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": model_id,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        # Send the request
        response = requests.post(self.base_url, headers=headers, json=payload)
        
        if response.status_code != 200:
            print(f"Error calling OpenRouter API: {response.status_code} {response.text}")
            return f"Error: {response.text}"
            
        result = response.json()
        
        # Extract the generated text
        try:
            generated_text = result["choices"][0]["message"]["content"]
            return generated_text
        except (KeyError, IndexError) as e:
            print(f"Error parsing OpenRouter response: {e}")
            return f"Error parsing response: {str(e)}"
    
    def is_multimodal(self, model_id: str) -> bool:
        """Check if model is multimodal."""
        # This is a simplification, as OpenRouter's multimodal support depends on the underlying model
        return any(model_id.startswith(model) for model in self.multimodal_models)

class ProviderFactory:
    """Factory for creating provider instances."""
    
    @staticmethod
    def get_provider(provider_name: str, api_key: str) -> ModelProvider:
        """Get a provider instance based on the provider name."""
        providers = {
            "google": GoogleProvider,
            "anthropic": AnthropicProvider,
            "openai": OpenAIProvider,
            "openrouter": OpenRouterProvider
        }
        
        if provider_name.lower() not in providers:
            raise ValueError(f"Unsupported provider: {provider_name}")
            
        provider_class = providers[provider_name.lower()]
        return provider_class(api_key)

class ModelManager:
    """Class to manage different model providers and configuration."""
    
    def __init__(self, config_path: str = None):
        """
        Initialize the Model Manager.
        
        Args:
            config_path: Path to the model configuration file
        """
        self.key_manager = LLMKeyManager()
        self.provider_instances = {}
        self.config = {}
        
        # Load configuration if provided
        if config_path:
            self.load_config(config_path)
    
    def load_config(self, config_path: str) -> None:
        """Load configuration from file."""
        try:
            with open(config_path, 'r') as f:
                self.config = json.load(f)
        except Exception as e:
            print(f"Error loading configuration: {e}")
            self.config = {}
    
    def get_provider(self, provider_name: str) -> Optional[ModelProvider]:
        """Get provider instance."""
        if provider_name in self.provider_instances:
            return self.provider_instances[provider_name]
            
        api_key = self.key_manager.get_api_key(provider_name)
        if not api_key:
            print(f"No API key found for provider: {provider_name}")
            return None
            
        try:
            provider = ProviderFactory.get_provider(provider_name, api_key)
            self.provider_instances[provider_name] = provider
            return provider
        except Exception as e:
            print(f"Error creating provider {provider_name}: {e}")
            return None
    
    def get_agent_model(self, agent_name: str) -> Dict[str, Any]:
        """Get the model configuration for a specific agent."""
        if not self.config or "agent_models" not in self.config:
            return {}
            
        agent_models = self.config["agent_models"]
        if agent_name in agent_models:
            return agent_models[agent_name]
            
        return {}
    
    def get_fallback_models(self, provider_name: str) -> List[str]:
        """Get fallback models for a specific provider."""
        if (not self.config or "agent_models" not in self.config or 
            "Fallback Options" not in self.config["agent_models"]):
            return []
            
        fallback_options = self.config["agent_models"]["Fallback Options"]
        provider_key = provider_name.capitalize()
        
        if provider_key in fallback_options:
            return fallback_options[provider_key].get("models", [])
            
        return []
    
    def test_providers(self) -> Dict[str, bool]:
        """Test all available providers."""
        results = {}
        available_providers = self.key_manager.get_all_available_providers()
        
        for provider_name in available_providers:
            provider = self.get_provider(provider_name)
            if not provider:
                results[provider_name] = False
                continue
                
            try:
                # Test with a simple prompt
                response = provider.generate(
                    "Hello, this is a test. Please respond with 'Test successful'.",
                    temperature=0.0,
                    max_tokens=20
                )
                
                results[provider_name] = "Test successful" in response
                print(f"Provider {provider_name} test: {'Success' if results[provider_name] else 'Failed'}")
            except Exception as e:
                print(f"Error testing provider {provider_name}: {e}")
                results[provider_name] = False
                
        return results

# Command-line interface for testing
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python model_provider.py [config_path]")
        sys.exit(1)
        
    config_path = sys.argv[1]
    manager = ModelManager(config_path)
    
    # Test all available providers
    print("Testing providers...")
    results = manager.test_providers()
    
    print("\nProvider Status:")
    for provider, status in results.items():
        print(f"- {provider}: {'Available' if status else 'Failed'}")
        
    print("\nAgent Model Configuration:")
    for agent_name in manager.config.get("agent_models", {}):
        if agent_name != "Fallback Options":
            model_config = manager.get_agent_model(agent_name)
            print(f"- {agent_name}: {model_config.get('provider', 'N/A')}/{model_config.get('model_id', 'N/A')}")
