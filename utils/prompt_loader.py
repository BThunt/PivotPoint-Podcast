"""
Prompt loader utility for managing external prompt files.
"""

import os
from pathlib import Path
from typing import Dict, Any

class PromptLoader:
    """Loads and manages prompts from external files."""
    
    def __init__(self, prompts_dir: str = "prompts"):
        """Initialize the prompt loader with the prompts directory."""
        self.prompts_dir = Path(prompts_dir)
        self._cache = {}
    
    def load_prompt(self, prompt_name: str) -> str:
        """Load a prompt from file, with caching."""
        if prompt_name in self._cache:
            return self._cache[prompt_name]
        
        prompt_file = self.prompts_dir / f"{prompt_name}.txt"
        
        if not prompt_file.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_file}")
        
        try:
            with open(prompt_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            self._cache[prompt_name] = content
            return content
            
        except Exception as e:
            raise RuntimeError(f"Error loading prompt '{prompt_name}': {str(e)}")
    
    def format_prompt(self, prompt_name: str, **kwargs) -> str:
        """Load and format a prompt with provided variables."""
        template = self.load_prompt(prompt_name)
        
        try:
            return template.format(**kwargs)
        except KeyError as e:
            raise ValueError(f"Missing required variable for prompt '{prompt_name}': {str(e)}")
    
    def reload_prompt(self, prompt_name: str) -> str:
        """Force reload a prompt from file (clears cache)."""
        if prompt_name in self._cache:
            del self._cache[prompt_name]
        return self.load_prompt(prompt_name)
    
    def list_available_prompts(self) -> list:
        """List all available prompt files."""
        if not self.prompts_dir.exists():
            return []
        
        return [f.stem for f in self.prompts_dir.glob("*.txt")]
    
    def clear_cache(self):
        """Clear the prompt cache."""
        self._cache.clear()

# Global instance for easy access
prompt_loader = PromptLoader()