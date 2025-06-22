import logging
import tiktoken
from typing import List, Dict, Any

from config.settings import Config
from utils.prompt_loader import prompt_loader
from utils.model_manager import model_manager

logger = logging.getLogger(__name__)

class ArticleAnalyzer:
    """Analyzes articles using GPT to select the most interesting ones by category."""
    
    def __init__(self):
        # Initialize tokenizer for counting tokens (used for OpenAI models)
        self.tokenizer = tiktoken.encoding_for_model("gpt-4")
        
        # Token limits - will be adjusted based on selected model
        if model_manager.should_apply_token_limits():
            # Token limits for GPT-4
            self.max_context_tokens = 8192
            self.max_message_tokens = 6000  # User requirement: never exceed 6000
            self.min_completion_tokens = 500  # Minimum for meaningful analysis
        else:
            # Much larger limits for Gemini
            self.max_context_tokens = model_manager.get_max_context_tokens()
            self.max_message_tokens = min(500000, self.max_context_tokens // 2)  # Use half for messages
            self.min_completion_tokens = 8000  # Much more generous for Gemini's detailed analysis
    
    def _count_tokens(self, text: str) -> int:
        """Count tokens in text using model-appropriate method."""
        if model_manager.should_apply_token_limits():
            # Use precise counting for OpenAI models
            try:
                return len(self.tokenizer.encode(text))
            except Exception as e:
                logger.warning(f"Token counting failed, using character estimate: {e}")
                return len(text) // 4
        else:
            # For Gemini, use model manager's estimation
            return model_manager.count_tokens_estimate(text)
    
    def _calculate_dynamic_limits(self, system_prompt: str, user_prompt_base: str) -> tuple[int, int]:
        """Calculate dynamic token limits based on prompt sizes."""
        system_tokens = self._count_tokens(system_prompt)
        base_user_tokens = self._count_tokens(user_prompt_base)
        
        # Reserve tokens for completion (reasonable amount)
        if model_manager.should_apply_token_limits():
            # Conservative for GPT-4
            completion_tokens = min(2000, self.max_context_tokens // 3)  # Max 2000 or 1/3 of context
        else:
            # More generous for Gemini
            completion_tokens = min(self.min_completion_tokens, self.max_context_tokens // 4)  # Use min_completion_tokens or 1/4 of context
        
        # Calculate max message tokens
        available_for_messages = self.max_context_tokens - completion_tokens
        max_message_tokens = min(self.max_message_tokens, available_for_messages)
        
        # Final check - ensure we don't exceed total context
        total_estimated = max_message_tokens + completion_tokens
        if total_estimated > self.max_context_tokens:
            # Reduce completion tokens if needed
            completion_tokens = self.max_context_tokens - max_message_tokens
            completion_tokens = max(self.min_completion_tokens, completion_tokens)
        
        logger.info(f"Token allocation: System={system_tokens}, Base User={base_user_tokens}, "
                   f"Max Message={max_message_tokens}, Max Completion={completion_tokens}")
        
        return max_message_tokens, completion_tokens
    
    def _trim_articles_to_fit(self, articles_by_category: Dict[str, List[Dict[str, Any]]],
                             max_message_tokens: int, system_prompt: str) -> str:
        """Trim articles to fit within token limits while maintaining balance across categories."""
        system_tokens = self._count_tokens(system_prompt)
        available_tokens = max_message_tokens - system_tokens - 100  # 100 token buffer
        
        # Start with full formatting and trim if needed
        formatted_articles = self._format_articles_by_category(articles_by_category)
        current_tokens = self._count_tokens(formatted_articles)
        
        if current_tokens <= available_tokens:
            logger.info(f"Articles fit within token limit: {current_tokens}/{available_tokens} tokens")
            return formatted_articles
        
        logger.warning(f"Articles exceed token limit: {current_tokens}/{available_tokens} tokens. Trimming...")
        
        # Calculate how much to trim from each article
        total_articles = sum(len(articles) for articles in articles_by_category.values())
        target_tokens_per_article = available_tokens // total_articles
        
        # Trim articles proportionally
        trimmed_sections = []
        for category, category_articles in articles_by_category.items():
            section = f"## {category}\n\n"
            
            for i, article in enumerate(category_articles, 1):
                # Use enhanced summary if available, fallback to snippet
                summary = article.get('summary', article.get('snippet', 'No summary available'))
                enhancement_info = ""
                if article.get('enhanced', False):
                    method = article.get('enhancement_method', 'unknown')
                    enhancement_info = f" (Enhanced via {method})"
                
                # Trim summary if too long
                summary_tokens = self._count_tokens(summary)
                if summary_tokens > target_tokens_per_article:
                    # Trim to target length (roughly)
                    target_chars = target_tokens_per_article * 4
                    summary = summary[:target_chars]
                    # Try to cut at sentence boundary
                    last_period = summary.rfind('.')
                    if last_period > target_chars * 0.7:
                        summary = summary[:last_period + 1]
                    summary += "... [trimmed]"
                
                article_text = f"""### Article {i}
**Title:** {article.get('title', 'No title')}
**Source:** {article.get('source', 'Unknown source')}
**Date:** {article.get('date', 'No date')}
**URL:** {article.get('url', 'No URL')}
**Summary:** {summary}{enhancement_info}

"""
                section += article_text
            
            trimmed_sections.append(section)
        
        final_content = "\n".join(trimmed_sections)
        final_tokens = self._count_tokens(final_content)
        logger.info(f"Trimmed articles to {final_tokens}/{available_tokens} tokens")
        
        return final_content

    def analyze_articles_by_category(self, articles: List[Dict[str, Any]]) -> tuple[str, List[Dict[str, Any]]]:
        """Analyze articles and select the most interesting ones by category.
        
        Returns:
            tuple: (analysis_text, selected_articles_list)
        """
        if not articles:
            logger.warning("No articles provided for analysis")
            return "No articles available for analysis.", []
        
        # Group articles by category
        articles_by_category = self._group_articles_by_category(articles)
        
        # Get prompts
        system_prompt = prompt_loader.load_prompt("article-analysis-system")
        # Use a sample user prompt for token calculation
        sample_user_prompt = "Articles by category:\n\n## Sample Category\n\n### Article 1\n**Title:** Sample\n**Summary:** Sample summary text for token calculation."
        
        # Calculate dynamic token limits
        max_message_tokens, max_completion_tokens = self._calculate_dynamic_limits(
            system_prompt, sample_user_prompt
        )
        
        # Trim articles to fit within token limits
        formatted_articles = self._trim_articles_to_fit(
            articles_by_category, max_message_tokens, system_prompt
        )
        
        # Format final user prompt
        user_prompt = prompt_loader.format_prompt("article-analysis-user",
                                                 articles_by_category=formatted_articles)
        
        # Final token check
        total_message_tokens = self._count_tokens(system_prompt) + self._count_tokens(user_prompt)
        if total_message_tokens > self.max_message_tokens:
            logger.error(f"Message tokens ({total_message_tokens}) exceed limit ({self.max_message_tokens})")
            # Emergency fallback: use original method with severe trimming
            return self._emergency_fallback_analysis(articles_by_category)
        
        try:
            logger.info(f"Analyzing articles with {Config.SELECTED_MODEL} (Message: {total_message_tokens} tokens, "
                       f"Completion: {max_completion_tokens} tokens)")
            analysis_result = model_manager.create_chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=max_completion_tokens,
                temperature=0.3  # Lower temperature for more consistent analysis
            )
            logger.info("Article analysis completed successfully")
            
            # Extract selected articles from the analysis
            selected_articles = self._extract_selected_articles(analysis_result, articles_by_category)
            logger.info(f"Extracted {len(selected_articles)} selected articles for podcast generation")
            
            return analysis_result, selected_articles
            
        except Exception as e:
            logger.error(f"Error analyzing articles: {str(e)}")
            return f"Error during article analysis: {str(e)}", []
    
    def _emergency_fallback_analysis(self, articles_by_category: Dict[str, List[Dict[str, Any]]]) -> tuple[str, List[Dict[str, Any]]]:
        """Emergency fallback when token limits are severely exceeded."""
        logger.warning("Using emergency fallback analysis with minimal content")
        
        # Create a very minimal summary
        fallback_content = "## Emergency Analysis Summary\n\n"
        selected_articles = []
        
        for category, category_articles in articles_by_category.items():
            if category_articles:
                # Just take the first article from each category
                article = category_articles[0]
                fallback_content += f"**{category}:** {article.get('title', 'No title')}\n"
                selected_articles.append(article)
        
        fallback_content += "\nNote: Analysis truncated due to content length limits."
        
        return fallback_content, selected_articles
    
    def _group_articles_by_category(self, articles: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group articles by their category."""
        categories = {}
        
        for article in articles:
            category = article.get("category", "Uncategorized")
            if category not in categories:
                categories[category] = []
            categories[category].append(article)
        
        logger.info(f"Grouped articles into {len(categories)} categories")
        for category, category_articles in categories.items():
            logger.info(f"  {category}: {len(category_articles)} articles")
        
        return categories
    
    def _format_articles_by_category(self, articles_by_category: Dict[str, List[Dict[str, Any]]]) -> str:
        """Format articles by category for GPT analysis."""
        formatted_sections = []
        
        for category, category_articles in articles_by_category.items():
            section = f"## {category}\n\n"
            
            for i, article in enumerate(category_articles, 1):
                # Use enhanced summary if available, fallback to snippet
                summary = article.get('summary', article.get('snippet', 'No summary available'))
                enhancement_info = ""
                if article.get('enhanced', False):
                    method = article.get('enhancement_method', 'unknown')
                    enhancement_info = f" (Enhanced via {method})"
                
                article_text = f"""### Article {i}
**Title:** {article.get('title', 'No title')}
**Source:** {article.get('source', 'Unknown source')}
**Date:** {article.get('date', 'No date')}
**URL:** {article.get('url', 'No URL')}
**Summary:** {summary}{enhancement_info}

"""
                section += article_text
            
            formatted_sections.append(section)
        
        return "\n".join(formatted_sections)
    
    def save_analysis_to_file(self, analysis: str, output_file: str) -> None:
        """Save the analysis result to a file."""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(analysis)
            logger.info(f"Article analysis saved to: {output_file}")
        except Exception as e:
            logger.error(f"Error saving analysis to file: {str(e)}")
            raise
    
    def _extract_selected_articles(self, analysis_text: str, articles_by_category: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """Extract the selected articles from the analysis text by matching URLs."""
        selected_articles = []
        
        # Extract URLs from the analysis text (handles both old and new formats)
        import re
        # New format: • **URL:** <url>
        url_pattern_new = r'• \*\*URL:\*\* (https?://[^\s\n]+)'
        # Old format: **URL:** <url>
        url_pattern_old = r'\*\*URL:\*\* (https?://[^\s\n]+)'
        
        selected_urls = re.findall(url_pattern_new, analysis_text)
        if not selected_urls:
            # Fallback to old format
            selected_urls = re.findall(url_pattern_old, analysis_text)
        
        logger.info(f"Found {len(selected_urls)} selected URLs in analysis")
        
        # Find the corresponding articles from the original list
        for category, category_articles in articles_by_category.items():
            for article in category_articles:
                article_url = article.get('url', '')
                if article_url in selected_urls:
                    # Add the article to selected list
                    selected_article = article.copy()
                    selected_article['selected_for_podcast'] = True
                    selected_articles.append(selected_article)
                    logger.info(f"Selected article from {category}: {article.get('title', 'No title')[:50]}...")
        
        # Sort selected articles by category order to maintain structure
        category_order = [
            "APTs & Cyber-Espionage",
            "Arrests & Cybercrime",
            "Breaches & Incidents",
            "Cybersecurity IPOs",
            "Cybersecurity Funding",
            "Cybersecurity M&A"
        ]
        
        def get_category_order(article):
            category = article.get('category', 'Unknown')
            try:
                return category_order.index(category)
            except ValueError:
                return len(category_order)  # Put unknown categories at the end
        
        selected_articles.sort(key=get_category_order)
        
        return selected_articles