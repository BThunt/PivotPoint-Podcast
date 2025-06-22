import openai
import logging
from typing import List, Dict, Any, Optional
from config.settings import Config

logger = logging.getLogger(__name__)

class ModelManager:
    """Manages AI model interactions, supporting both OpenAI and Gemini via OpenRouter."""
    
    def __init__(self):
        self.model = None
        self.model_name = None
        self.max_input_tokens = None
        self.max_output_tokens = None
        self.client = None
        # Don't setup client immediately - wait until first use
    
    def _setup_client(self):
        """Setup the appropriate client based on selected model."""
        # Get current model, defaulting to 'openai' if not set
        current_model = getattr(Config, 'SELECTED_MODEL', 'openai')
        
        # Only reconfigure if model has changed
        if self.model == current_model:
            return
            
        self.model = current_model
        self._configure_for_model()
    
    def _configure_for_model(self):
        """Configure the client for the current model."""
        if self.model == "gemini":
            # Configure OpenAI client to use OpenRouter for Gemini 2.5 Pro
            self.client = openai.OpenAI(
                api_key=Config.OPEN_ROUTER_API_KEY,
                base_url="https://openrouter.ai/api/v1"
            )
            self.model_name = "google/gemini-2.5-pro-preview"
            self.max_input_tokens = 1048576  # 1M tokens
            self.max_output_tokens = 65536   # 64K tokens
            logger.info("Configured for Gemini 2.5 Pro via OpenRouter")
        elif self.model == "gemini-flash":
            # Configure OpenAI client to use OpenRouter for Gemini Flash Lite
            self.client = openai.OpenAI(
                api_key=Config.OPEN_ROUTER_API_KEY,
                base_url="https://openrouter.ai/api/v1"
            )
            self.model_name = "google/gemini-2.5-flash-lite-preview-06-17"
            self.max_input_tokens = 1048576  # 1M tokens (same as Pro)
            self.max_output_tokens = 8192    # 8K tokens (Flash Lite has lower output limit)
            logger.info("Configured for Gemini 2.5 Flash Lite via OpenRouter")
        else:
            # Standard OpenAI configuration
            self.client = openai.OpenAI(
                api_key=Config.OPENAI_API_KEY
            )
            self.model_name = "gpt-4"
            self.max_input_tokens = 8192     # GPT-4 context limit
            self.max_output_tokens = 4096    # Conservative GPT-4 output limit
            logger.info("Configured for OpenAI GPT-4")
    
    def create_chat_completion(self, messages: List[Dict[str, str]], 
                             max_tokens: Optional[int] = None, 
                             temperature: float = 0.7) -> str:
        """Create a chat completion using the selected model."""
        
        # Ensure client is configured for current model
        self._setup_client()
        
        # Use model-specific max tokens if not specified
        if max_tokens is None:
            if self.model == "gemini":
                max_tokens = min(self.max_output_tokens, 12000)  # Leverage Gemini Pro's full capacity
            elif self.model == "gemini-flash":
                max_tokens = min(self.max_output_tokens, 6000)   # Optimize for Flash Lite's 8K limit
            else:
                max_tokens = min(self.max_output_tokens, 2000)   # Conservative for OpenAI
        
        # For Gemini models, ensure we're using adequate tokens for complex tasks
        if self.model == "gemini" and max_tokens < 8000:
            max_tokens = min(self.max_output_tokens, 12000)  # Use Gemini Pro's full potential
        elif self.model == "gemini-flash" and max_tokens < 4000:
            max_tokens = min(self.max_output_tokens, 6000)   # Optimize for Flash Lite
        
        try:
            logger.info(f"Creating chat completion with {self.model_name} (max_tokens: {max_tokens})")
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            content = response.choices[0].message.content
            logger.info(f"Successfully generated response ({len(content)} characters)")
            return content
            
        except Exception as e:
            logger.error(f"Error creating chat completion with {self.model_name}: {str(e)}")
            raise
    
    def count_tokens_estimate(self, text: str) -> int:
        """Estimate token count for the text.
        
        For Gemini, we use a more conservative estimate since we have much larger limits.
        For OpenAI, we use the existing tiktoken-based counting.
        """
        # Ensure client is set up
        self._setup_client()
        
        if self.model in ["gemini", "gemini-flash"]:
            # Gemini models have huge token limits, so we can be more relaxed
            # Use a simple character-based estimate: ~3 chars per token for Gemini
            return len(text) // 3
        else:
            # For OpenAI, use more precise counting (handled by existing code)
            # Fallback estimate: 4 characters per token
            return len(text) // 4
    
    def should_apply_token_limits(self) -> bool:
        """Return whether strict token limits should be applied."""
        # Ensure client is set up
        self._setup_client()
        # Only apply strict limits for OpenAI models
        return self.model not in ["gemini", "gemini-flash"]
    
    def get_max_context_tokens(self) -> int:
        """Get maximum context tokens for the current model."""
        # Ensure client is set up
        self._setup_client()
        return self.max_input_tokens
    
    def get_max_output_tokens(self) -> int:
        """Get maximum output tokens for the current model."""
        # Ensure client is set up
        self._setup_client()
        return self.max_output_tokens

# Global model manager instance
model_manager = ModelManager()