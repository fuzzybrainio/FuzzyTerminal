import os
import asyncio
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
import json

# Provider imports will be loaded lazily

class LLMProvider(ABC):
    """Abstract Base Class for Async LLM Providers"""
    
    @abstractmethod
    async def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate text from a prompt asynchronously"""
        pass
    
    @abstractmethod
    async def get_suggestions(self, context: str) -> List[Dict[str, str]]:
        """Get command suggestions based on context asynchronously"""
        pass

class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20240620"):
        try:
            import anthropic
        except ImportError:
            raise ImportError("anthropic package is not installed")
        self.client = anthropic.AsyncAnthropic(api_key=api_key)
        self.model = model

    async def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        messages = [{"role": "user", "content": prompt}]
        kwargs = {"model": self.model, "max_tokens": 2000, "messages": messages}
        if system_prompt:
            kwargs["system"] = system_prompt
            
        response = await self.client.messages.create(**kwargs)
        return response.content[0].text

    async def get_suggestions(self, context: str) -> List[Dict[str, str]]:
        prompt = f"""
{context}

Task: Suggest 3 relevant shell commands based on the user input.
Format: Return ONLY a JSON array of objects with 'command' and 'explanation' keys.
Example: [{{"command": "ls -la", "explanation": "List all files"}}]
"""
        try:
            response = await self.generate_text(prompt)
            return self._parse_json(response)
        except Exception as e:
            print(f"Anthropic Error: {e}")
            return []

    def _parse_json(self, text: str) -> List[Dict]:
        text = text.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        return json.loads(text)

class OllamaProvider(LLMProvider):
    def __init__(self, model: str = "llama3", base_url: str = "http://localhost:11434"):
        try:
            import ollama
        except ImportError:
            raise ImportError("ollama package is not installed")
        self.client = ollama.AsyncClient(host=base_url)
        self.model = model

    async def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = await self.client.chat(model=self.model, messages=messages)
        return response['message']['content']

    async def get_suggestions(self, context: str) -> List[Dict[str, str]]:
        prompt = f"""
{context}

Task: Suggest 3 relevant shell commands based on the user input.
Return ONLY a JSON array. No markdown, no explanation text outside the JSON.
Example: [{{"command": "ls -la", "explanation": "List all files"}}]
"""
        try:
            response = await self.generate_text(prompt)
            return self._parse_json(response)
        except Exception as e:
            print(f"Ollama Error: {e}")
            return []

    def _parse_json(self, text: str) -> List[Dict]:
        text = text.strip()
        start = text.find('[')
        end = text.rfind(']') + 1
        if start != -1 and end != -1:
            return json.loads(text[start:end])
        return []

class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "gemini-1.5-pro"):
        if not api_key:
            raise ValueError("Gemini API Key is required")
        try:
            import google.generativeai as genai
        except ImportError:
            raise ImportError("google-generativeai package is not installed")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model or "gemini-1.5-pro")

    async def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"System: {system_prompt}\nUser: {prompt}"
            
        # Run synchronous call in executor
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, self.model.generate_content, full_prompt)
        return response.text

    async def get_suggestions(self, context: str) -> List[Dict[str, str]]:
        prompt = f"""
{context}

Task: Suggest 3 relevant shell commands based on the user input.
Return ONLY a JSON array.
Example: [{{"command": "ls -la", "explanation": "List all files"}}]
"""
        try:
            response = await self.generate_text(prompt)
            return self._parse_json(response)
        except Exception as e:
            print(f"Gemini Error: {e}")
            return []

    def _parse_json(self, text: str) -> List[Dict]:
        text = text.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        return json.loads(text)

class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise ImportError("openai package is not installed")
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages
        )
        return response.choices[0].message.content

    async def get_suggestions(self, context: str) -> List[Dict[str, str]]:
        prompt = f"""
{context}

Task: Suggest 3 relevant shell commands based on the user input.
Return ONLY a JSON array.
Example: [{{"command": "ls -la", "explanation": "List all files"}}]
"""
        try:
            response = await self.generate_text(prompt)
            return self._parse_json(response)
        except Exception as e:
            print(f"OpenAI Error: {e}")
            return []

    def _parse_json(self, text: str) -> List[Dict]:
        text = text.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        return json.loads(text)

class DeepSeekProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "deepseek-chat"):
        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise ImportError("openai package is not installed")
        self.client = AsyncOpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        self.model = model

    async def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages
        )
        return response.choices[0].message.content

    async def get_suggestions(self, context: str) -> List[Dict[str, str]]:
        prompt = f"""
{context}

Task: Suggest 3 relevant shell commands based on the user input.
Return ONLY a JSON array.
Example: [{{"command": "ls -la", "explanation": "List all files"}}]
"""
        try:
            response = await self.generate_text(prompt)
            return self._parse_json(response)
        except Exception as e:
            print(f"DeepSeek Error: {e}")
            return []

    def _parse_json(self, text: str) -> List[Dict]:
        text = text.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        return json.loads(text)

class OpenAICompatibleProvider(LLMProvider):
    """Handles OpenRouter, Grok, and standard OpenAI (Async)"""
    def __init__(self, api_key: str, base_url: str, model: str):
        try:
            from openai import AsyncOpenAI
        except ImportError:
            raise ImportError("openai package is not installed")
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    async def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages
        )
        return response.choices[0].message.content

    async def get_suggestions(self, context: str) -> List[Dict[str, str]]:
        prompt = f"""
{context}

Task: Suggest 3 relevant shell commands based on the user input.
Return ONLY a JSON array.
Example: [{{"command": "ls -la", "explanation": "List all files"}}]
"""
        try:
            response = await self.generate_text(prompt)
            return self._parse_json(response)
        except Exception as e:
            print(f"Provider Error: {e}")
            return []

    def _parse_json(self, text: str) -> List[Dict]:
        text = text.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        return json.loads(text)

class ProviderFactory:
    @staticmethod
    def create(config: Dict) -> Optional[LLMProvider]:
        provider_type = config.get("provider", "anthropic")
        providers_config = config.get("providers", {})
        
        cfg = providers_config.get(provider_type, {})
        
        if provider_type == "anthropic":
            return AnthropicProvider(api_key=cfg.get("api_key"), model=cfg.get("model") or "claude-3-5-sonnet-20240620")
            
        elif provider_type == "openai":
            return OpenAIProvider(api_key=cfg.get("api_key"), model=cfg.get("model") or "gpt-4o")

        elif provider_type == "deepseek":
            return DeepSeekProvider(api_key=cfg.get("api_key"), model=cfg.get("model") or "deepseek-chat")

        elif provider_type == "ollama":
            return OllamaProvider(model=cfg.get("model") or "llama3", base_url=cfg.get("base_url") or "http://localhost:11434")
            
        elif provider_type == "gemini":
            return GeminiProvider(api_key=cfg.get("api_key"), model=cfg.get("model") or "gemini-1.5-pro")
            
        elif provider_type == "openrouter":
            return OpenAICompatibleProvider(
                api_key=cfg.get("api_key"),
                base_url=cfg.get("base_url") or "https://openrouter.ai/api/v1",
                model=cfg.get("model") or "openai/gpt-3.5-turbo"
            )
            
        elif provider_type == "grok":
            return OpenAICompatibleProvider(
                api_key=cfg.get("api_key"),
                base_url=cfg.get("base_url") or "https://api.x.ai/v1",
                model=cfg.get("model") or "grok-beta"
            )
            
        return None
