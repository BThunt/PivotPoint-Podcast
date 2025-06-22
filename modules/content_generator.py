import logging
from typing import List, Dict, Any

from config.settings import Config
from utils.helpers import truncate_text, estimate_reading_time, format_podcast_intro, format_podcast_outro
from utils.prompt_loader import prompt_loader
from utils.model_manager import model_manager

logger = logging.getLogger(__name__)

class ContentGenerator:
    """Generates podcast content using OpenAI."""
    
    def __init__(self):
        self.target_length = Config.PODCAST_LENGTH_MINUTES
    
    def create_podcast_script(self, articles: List[Dict[str, Any]]) -> str:
        """Create a podcast script from news articles."""
        if not articles:
            logger.warning("No articles provided for script generation")
            return self._create_fallback_script()
        
        # Prepare articles summary for the AI
        articles_text = self._format_articles_for_ai(articles)
        
        # Create the prompt
        system_prompt = self._get_system_prompt()
        user_prompt = self._get_user_prompt(articles_text)
        
        try:
            # Use model-appropriate token limits
            if model_manager.should_apply_token_limits():
                max_tokens = 2000  # Conservative for OpenAI
            else:
                max_tokens = 8000  # Leverage Gemini's full output capacity
            
            logger.info(f"Generating podcast script with {Config.SELECTED_MODEL} (max_tokens: {max_tokens})")
            script_content = model_manager.create_chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.7
            )
            
            # Add intro and outro
            full_script = self._format_full_script(script_content)
            
            # Validate script length
            estimated_time = estimate_reading_time(full_script)
            logger.info(f"Generated script with estimated reading time: {estimated_time:.1f} minutes")
            
            return full_script
            
        except Exception as e:
            logger.error(f"Error generating podcast script: {str(e)}")
            return self._create_fallback_script()
    
    def _format_articles_for_ai(self, articles: List[Dict[str, Any]]) -> str:
        """Format articles for AI processing."""
        formatted_articles = []
        
        for i, article in enumerate(articles, 1):
            # Use enhanced summary if available, fallback to snippet
            summary = article.get('summary', article.get('snippet', 'No summary available'))
            enhancement_info = ""
            if article.get('enhanced', False):
                method = article.get('enhancement_method', 'unknown')
                enhancement_info = f" (Enhanced via {method})"
            
            article_text = f"""
Article {i}:
Title: {article.get('title', 'No title')}
Source: {article.get('source', 'Unknown source')}
Date: {article.get('date', 'No date')}
Summary: {summary}{enhancement_info}
URL: {article.get('url', 'No URL')}
"""
            formatted_articles.append(article_text.strip())
        
        return "\n\n".join(formatted_articles)
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for script generation."""
        return prompt_loader.format_prompt("podcast-script-system", target_length=self.target_length)
    
    def _get_user_prompt(self, articles_text: str) -> str:
        """Get the user prompt with articles."""
        # Use model-appropriate text limits
        if model_manager.should_apply_token_limits():
            # Conservative truncation for OpenAI
            processed_articles = truncate_text(articles_text, 3000)
        else:
            # Use full text for Gemini models to maximize context
            processed_articles = articles_text
            logger.info(f"Using full articles text for Gemini ({len(articles_text)} characters)")
        
        return prompt_loader.format_prompt(
            "podcast-script-user",
            target_length=self.target_length,
            articles_text=processed_articles
        )
    
    def _format_full_script(self, content: str) -> str:
        """Format the complete script with intro and outro."""
        # The new PivotPoint Podcast system prompt includes its own intro/outro
        # so we return the content as-is to avoid duplication
        return content
    
    def _create_fallback_script(self) -> str:
        """Create a fallback script when no articles are available or AI fails."""
        # For fallback, we'll create a PivotPoint Podcast format manually
        fallback_content = prompt_loader.load_prompt("fallback-script-content")
        
        return f"""This is the PivotPoint Podcast. I'm [Your Name].

{fallback_content}

That's all for today's PivotPoint Podcast. I'm [Your Name] — thanks for listening."""
    
    def summarize_articles(self, articles: List[Dict[str, Any]]) -> str:
        """Create a brief summary of articles for logging/debugging."""
        if not articles:
            return "No articles to summarize"
        
        summary_parts = []
        for article in articles[:3]:  # Just top 3 for summary
            title = article.get('title', 'No title')
            source = article.get('source', 'Unknown')
            summary_parts.append(f"• {title} ({source})")
        
        if len(articles) > 3:
            summary_parts.append(f"• ... and {len(articles) - 3} more articles")
        
        return "\n".join(summary_parts)