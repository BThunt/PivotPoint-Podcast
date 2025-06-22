import requests
import logging
import json
import sqlite3
import hashlib
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path

import tiktoken
import trafilatura
from newspaper import Article

from config.settings import Config
from utils.model_manager import model_manager

logger = logging.getLogger(__name__)

class ArticleEnhancer:
    """Enhances articles by fetching full content and generating GPT summaries."""
    
    def __init__(self, cache_dir: Optional[str] = None):
        """Initialize the article enhancer.
        
        Args:
            cache_dir: Directory for SQLite cache. If None, uses output directory.
        """
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        })
        
        # Initialize tokenizer for counting tokens
        self.tokenizer = tiktoken.encoding_for_model("gpt-3.5-turbo")
        
        # Set up cache directory
        if cache_dir is None:
            cache_dir = Path(Config.OUTPUT_DIR) / "cache" if Config.OUTPUT_DIR else Path("cache")
        else:
            cache_dir = Path(cache_dir)
        
        cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_db_path = cache_dir / "articles.db"
        
        # Initialize cache database
        self._init_cache_db()
        
        # Configuration for article processing
        self.max_article_tokens = 5000  # ~20,000 characters
        self.per_article_budget = 180   # tokens for summary (can be adjusted based on total articles)
        self.fetch_timeout = 15
        
        # Model configuration will be handled by model_manager
    
    def _init_cache_db(self):
        """Initialize the SQLite cache database."""
        try:
            with sqlite3.connect(self.cache_db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS article_cache (
                        url_hash TEXT PRIMARY KEY,
                        url TEXT NOT NULL,
                        summary TEXT NOT NULL,
                        fetched_at TIMESTAMP NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_url ON article_cache(url)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_fetched_at ON article_cache(fetched_at)")
                conn.commit()
                logger.info(f"Initialized article cache database at {self.cache_db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize cache database: {e}")
            raise
    
    def _get_url_hash(self, url: str) -> str:
        """Generate a hash for the URL for cache lookup."""
        return hashlib.sha256(url.encode('utf-8')).hexdigest()
    
    def _get_cached_summary(self, url: str, max_age_hours: int = 24) -> Optional[str]:
        """Get cached summary if it exists and is fresh enough."""
        url_hash = self._get_url_hash(url)
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        try:
            with sqlite3.connect(self.cache_db_path) as conn:
                cursor = conn.execute(
                    "SELECT summary FROM article_cache WHERE url_hash = ? AND fetched_at > ?",
                    (url_hash, cutoff_time)
                )
                result = cursor.fetchone()
                if result:
                    logger.info(f"Cache hit for URL: {url[:50]}...")
                    return result[0]
        except Exception as e:
            logger.warning(f"Cache lookup failed: {e}")
        
        return None
    
    def _cache_summary(self, url: str, summary: str):
        """Cache the summary for future use."""
        url_hash = self._get_url_hash(url)
        fetched_at = datetime.now()
        
        try:
            with sqlite3.connect(self.cache_db_path) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO article_cache (url_hash, url, summary, fetched_at) VALUES (?, ?, ?, ?)",
                    (url_hash, url, summary, fetched_at)
                )
                conn.commit()
                logger.debug(f"Cached summary for URL: {url[:50]}...")
        except Exception as e:
            logger.warning(f"Failed to cache summary: {e}")
    
    def _fetch_article_content(self, url: str) -> Optional[str]:
        """Fetch and extract readable text from article URL."""
        try:
            logger.info(f"Fetching article: {url[:50]}...")
            response = self.session.get(url, timeout=self.fetch_timeout)
            response.raise_for_status()
            
            html_content = response.text
            
            # Try trafilatura first (preferred method)
            extracted_text = trafilatura.extract(html_content)
            
            if extracted_text and len(extracted_text.strip()) > 100:
                logger.info(f"Successfully extracted text using trafilatura ({len(extracted_text)} chars)")
                return extracted_text
            
            # Fallback to newspaper3k
            logger.info("Trafilatura extraction insufficient, trying newspaper3k...")
            article = Article(url)
            article.set_html(html_content)
            article.parse()
            
            if article.text and len(article.text.strip()) > 100:
                # Combine headline, author, date, and text
                content_parts = []
                if article.title:
                    content_parts.append(f"Title: {article.title}")
                if hasattr(article, 'authors') and article.authors:
                    content_parts.append(f"Author: {', '.join(article.authors)}")
                if article.publish_date:
                    content_parts.append(f"Date: {article.publish_date}")
                content_parts.append(f"Content: {article.text}")
                
                extracted_text = "\n\n".join(content_parts)
                logger.info(f"Successfully extracted text using newspaper3k ({len(extracted_text)} chars)")
                return extracted_text
            
            logger.warning(f"Both extraction methods failed for URL: {url}")
            return None
            
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout fetching article: {url}")
            return None
        except requests.exceptions.RequestException as e:
            logger.warning(f"Request failed for {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching article {url}: {e}")
            return None
    
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
    
    def _trim_article_content(self, content: str) -> str:
        """Trim article content to fit within token limits."""
        # Skip trimming for Gemini due to large token limits
        if not model_manager.should_apply_token_limits():
            logger.info(f"Using full article content for Gemini ({len(content)} characters)")
            return content
        
        token_count = self._count_tokens(content)
        
        if token_count <= self.max_article_tokens:
            return content
        
        logger.info(f"Article too long ({token_count} tokens), trimming to {self.max_article_tokens} tokens")
        
        # Rough estimate: 4 characters per token
        target_chars = self.max_article_tokens * 4
        trimmed_content = content[:target_chars]
        
        # Try to cut at a sentence boundary
        last_period = trimmed_content.rfind('.')
        if last_period > target_chars * 0.8:  # If we can cut at a sentence within 80% of target
            trimmed_content = trimmed_content[:last_period + 1]
        
        logger.info(f"Trimmed article to {len(trimmed_content)} characters")
        return trimmed_content
    
    def _generate_gpt_summary(self, article_text: str, per_article_budget: int) -> str:
        """Generate AI summary of the article."""
        system_prompt = f"""You are a cybersecurity analyst. Write an executive brief of up to {per_article_budget} tokens (6–8 sentences). Include, when available, who is involved, who/what is affected, technique or vulnerability, business or operational impact, and at least one practical takeaway. Skip elements absent from the source."""
        
        user_prompt = f"Article text:\n---\n{article_text}"
        
        try:
            summary = model_manager.create_chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=per_article_budget,
                temperature=0.3
            )
            
            summary = summary.strip()
            logger.info(f"Generated AI summary ({len(summary)} chars)")
            return summary
            
        except Exception as e:
            logger.error(f"AI summary generation failed: {e}")
            return "(AI summary generation failed)"
    
    def _calculate_per_article_budget(self, num_articles: int) -> int:
        """Calculate per-article token budget based on total articles."""
        if not model_manager.should_apply_token_limits():
            # For Gemini, be much more generous with token budget
            return min(1000, 8000 // max(1, num_articles))  # Up to 1000 tokens per article
        
        # Original logic for OpenAI models
        # Target: ≤ 60 articles at ≤ 180 tokens each + 800 tokens selection prompt ≤ 10,600 tokens
        # With 1,000 token reply buffer, total ≤ 12,000 tokens (well under 16k limit)
        
        if num_articles <= 60:
            return 180  # Optimal budget
        else:
            # Scale down if more articles
            available_tokens = 10600 - 800  # Total budget minus selection prompt
            return max(120, available_tokens // num_articles)  # Minimum 120 tokens per article
    
    def enhance_articles(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Enhance articles by replacing snippets with GPT-generated summaries.
        
        Args:
            articles: List of article dictionaries with Serper data
            
        Returns:
            List of enhanced articles with GPT summaries
        """
        if not articles:
            logger.warning("No articles provided for enhancement")
            return articles
        
        logger.info(f"Enhancing {len(articles)} articles with GPT summaries")
        
        # Calculate per-article budget
        per_article_budget = self._calculate_per_article_budget(len(articles))
        logger.info(f"Using per-article budget of {per_article_budget} tokens")
        
        enhanced_articles = []
        
        for i, article in enumerate(articles, 1):
            logger.info(f"Processing article {i}/{len(articles)}: {article.get('title', 'No title')[:50]}...")
            
            # Step 1: Add unique ID if not present
            if 'id' not in article:
                article['id'] = uuid.uuid4().hex
            
            url = article.get('url', '')
            if not url:
                logger.warning(f"Article {i} has no URL, keeping original snippet")
                enhanced_articles.append(article)
                continue
            
            # Step 9: Check cache first
            cached_summary = self._get_cached_summary(url)
            if cached_summary:
                article['summary'] = cached_summary
                article['enhanced'] = True
                article['enhancement_method'] = 'cache'
                enhanced_articles.append(article)
                continue
            
            # Step 2: Fetch the article
            article_content = self._fetch_article_content(url)
            
            if not article_content:
                # Keep original snippet on fetch failure
                article['summary'] = article.get('snippet', '(fetch failed)')
                article['enhanced'] = False
                article['enhancement_method'] = 'fetch_failed'
                enhanced_articles.append(article)
                continue
            
            # Step 4: Trim if enormous
            trimmed_content = self._trim_article_content(article_content)
            
            # Step 5: Summarize with GPT
            gpt_summary = self._generate_gpt_summary(trimmed_content, per_article_budget)
            
            # Step 6: Overwrite the Serper snippet
            article['summary'] = gpt_summary
            article['enhanced'] = True
            article['enhancement_method'] = 'gpt_generated'
            article['original_snippet'] = article.get('snippet', '')  # Preserve original
            
            # Cache the summary
            self._cache_summary(url, gpt_summary)
            
            enhanced_articles.append(article)
        
        # Step 7: Log enhancement results
        enhanced_count = sum(1 for a in enhanced_articles if a.get('enhanced', False))
        logger.info(f"Enhancement complete: {enhanced_count}/{len(articles)} articles enhanced")
        
        return enhanced_articles
    
    def save_enhanced_articles(self, articles: List[Dict[str, Any]], output_file: str):
        """Save enhanced articles to JSON file."""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(articles, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved enhanced articles to {output_file}")
        except Exception as e:
            logger.error(f"Failed to save enhanced articles: {e}")
            raise