"""
Search configuration loader utility for managing external search configuration files.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any

class SearchConfigLoader:
    """Loads and manages search configurations from external files."""
    
    def __init__(self, search_configs_dir: str = "search_configs"):
        """Initialize the search config loader with the search configs directory."""
        self.search_configs_dir = Path(search_configs_dir)
        self._cache = {}
        self._parameters = None
    
    def load_parameters(self) -> Dict[str, Any]:
        """Load search parameters from JSON file, with caching."""
        if self._parameters is not None:
            return self._parameters
        
        params_file = self.search_configs_dir / "search-parameters.json"
        
        if not params_file.exists():
            raise FileNotFoundError(f"Search parameters file not found: {params_file}")
        
        try:
            with open(params_file, 'r', encoding='utf-8') as f:
                self._parameters = json.load(f)
            return self._parameters
            
        except Exception as e:
            raise RuntimeError(f"Error loading search parameters: {str(e)}")
    
    def load_keywords_list(self, config_name: str) -> List[str]:
        """Load a list of keywords from a text file, with caching."""
        if config_name in self._cache:
            return self._cache[config_name]
        
        config_file = self.search_configs_dir / f"{config_name}.txt"
        
        if not config_file.exists():
            raise FileNotFoundError(f"Search config file not found: {config_file}")
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Filter out empty lines and comments
            keywords = []
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#'):
                    keywords.append(line)
            
            self._cache[config_name] = keywords
            return keywords
            
        except Exception as e:
            raise RuntimeError(f"Error loading search config '{config_name}': {str(e)}")
    
    def get_basic_keywords(self) -> List[str]:
        """Get the basic search keywords."""
        return self.load_keywords_list("basic-keywords")
    
    def get_relevance_keywords(self) -> List[str]:
        """Get the relevance filtering keywords."""
        return self.load_keywords_list("relevance-keywords")
    
    def get_google_dorks(self) -> List[str]:
        """Get the Google Dorks search queries."""
        return self.load_keywords_list("google-dorks")
    
    def get_active_search_queries(self) -> List[str]:
        """Get the currently active search queries based on configuration."""
        params = self.load_parameters()
        search_modes = params.get("search_modes", {})
        
        active_queries = []
        
        # Check if basic keywords are enabled
        if search_modes.get("basic_keywords", {}).get("enabled", True):
            active_queries.extend(self.get_basic_keywords())
        
        # Check if Google Dorks are enabled
        if search_modes.get("google_dorks", {}).get("enabled", False):
            active_queries.extend(self.get_google_dorks())
        
        return active_queries
    
    def get_api_settings(self) -> Dict[str, Any]:
        """Get API configuration settings."""
        params = self.load_parameters()
        return params.get("api_settings", {})
    
    def get_date_filter_settings(self) -> Dict[str, Any]:
        """Get date filtering settings."""
        params = self.load_parameters()
        return params.get("date_filters", {})
    
    def get_filtering_settings(self) -> Dict[str, Any]:
        """Get content filtering settings."""
        params = self.load_parameters()
        return params.get("filtering", {})
    
    def get_content_requirements(self) -> Dict[str, Any]:
        """Get content validation requirements."""
        params = self.load_parameters()
        return params.get("content_requirements", {})
    
    def is_search_mode_enabled(self, mode: str) -> bool:
        """Check if a specific search mode is enabled."""
        params = self.load_parameters()
        search_modes = params.get("search_modes", {})
        return search_modes.get(mode, {}).get("enabled", False)
    
    def reload_config(self, config_name: str = None):
        """Force reload a configuration from file (clears cache)."""
        if config_name:
            if config_name in self._cache:
                del self._cache[config_name]
        else:
            # Reload all
            self._cache.clear()
            self._parameters = None
    
    def list_available_configs(self) -> List[str]:
        """List all available configuration files."""
        if not self.search_configs_dir.exists():
            return []
        
        configs = []
        for f in self.search_configs_dir.glob("*.txt"):
            configs.append(f.stem)
        for f in self.search_configs_dir.glob("*.json"):
            configs.append(f.stem)
        
        return configs
    
    def clear_cache(self):
        """Clear the configuration cache."""
        self._cache.clear()
        self._parameters = None

# Global instance for easy access
search_config_loader = SearchConfigLoader()