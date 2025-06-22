import requests
import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta

from config.settings import Config
from utils.helpers import get_date_range, format_date_for_search
from utils.search_config_loader import search_config_loader

logger = logging.getLogger(__name__)

class NewsCollector:
    """Collects cybersecurity news from various sources."""
    
    def __init__(self):
        self.api_key = Config.SERPER_API_KEY
        self.session = requests.Session()
        
        # Load API settings from configuration
        api_settings = search_config_loader.get_api_settings()
        self.base_url = api_settings.get("base_url", "https://google.serper.dev/news")
        self.timeout = api_settings.get("timeout", 10)
        self.num_results = api_settings.get("num_results", 10)
        self.geographic_location = api_settings.get("geographic_location", "us")
        self.language = api_settings.get("language", "en")
        
        # Load date filter settings
        self.date_settings = search_config_loader.get_date_filter_settings()
        
        # Load filtering settings
        self.filtering_settings = search_config_loader.get_filtering_settings()
    
    def search_news(self, query: str, days_back: int = None) -> List[Dict[str, Any]]:
        """Search for news articles using SerperAPI."""
        if days_back is None:
            days_back = self.date_settings.get("default_days_back", 1)
            
        start_date, end_date = get_date_range(days_back)
        
        # Format the search query with date filters
        date_filter = f"after:{format_date_for_search(start_date)} before:{format_date_for_search(end_date)}"
        full_query = f"{query} {date_filter}"
        
        headers = {"X-API-KEY": self.api_key}
        payload = {
            "q": full_query,
            "num": self.num_results,
            "gl": self.geographic_location,
            "hl": self.language
        }
        
        try:
            logger.info(f"Searching for: {query}")
            response = self.session.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            articles = data.get("news", [])
            
            # Clean and structure the articles
            cleaned_articles = []
            for article in articles:
                cleaned_article = {
                    "title": article.get("title", "").strip(),
                    "snippet": article.get("snippet", "").strip(),
                    "url": article.get("link", ""),
                    "source": article.get("source", ""),
                    "date": article.get("date", ""),
                    "query": query
                }
                
                # Only include articles with meaningful content
                if cleaned_article["title"] and cleaned_article["snippet"]:
                    cleaned_articles.append(cleaned_article)
            
            logger.info(f"Found {len(cleaned_articles)} articles for query: {query}")
            return cleaned_articles
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error searching for news with query '{query}': {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error during news search: {str(e)}")
            return []
    
    def collect_daily_news(self) -> List[Dict[str, Any]]:
        """Collect news from all configured search queries."""
        all_articles = []
        category_counts = {}
        
        # Get active search queries from configuration
        search_queries = search_config_loader.get_active_search_queries()
        
        # Check if we're using Google Dorks mode (which has categories)
        is_google_dorks = search_config_loader.is_search_mode_enabled("google_dorks")
        max_per_category = self.filtering_settings.get("max_articles_per_category", 5)
        
        # Define category names for Google Dorks
        category_names = [
            "APTs & Cyber-Espionage",
            "Arrests & Cybercrime",
            "Breaches & Incidents",
            "Cybersecurity IPOs",
            "Cybersecurity Funding",
            "Cybersecurity M&A"
        ]
        
        for i, query in enumerate(search_queries):
            articles = self.search_news(query)
            
            # Determine category name
            if is_google_dorks and i < len(category_names):
                category_name = category_names[i]
            else:
                category_name = f"Query_{i+1}"
            
            # If using Google Dorks, limit articles per category (query)
            if is_google_dorks and articles:
                articles = articles[:max_per_category]
                logger.info(f"Category '{category_name}': Limited to {len(articles)} articles")
            
            # Add category/query info to each article
            for article in articles:
                article["search_query"] = query
                article["category"] = category_name
                article["search_mode"] = "google_dorks" if is_google_dorks else "basic_keywords"
            
            all_articles.extend(articles)
            category_counts[category_name] = len(articles)
        
        # Remove duplicates based on URL
        seen_urls = set()
        unique_articles = []
        
        for article in all_articles:
            url = article.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_articles.append(article)
        
        # Log category breakdown
        if is_google_dorks:
            logger.info("Category breakdown:")
            for category, count in category_counts.items():
                logger.info(f"  {category}: {count} articles")
        
        logger.info(f"Collected {len(unique_articles)} unique articles from {len(search_queries)} queries")
        return unique_articles
    
    def filter_relevant_articles(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter articles for relevance to cybersecurity professionals."""
        # Load relevance keywords from configuration
        high_value_keywords = search_config_loader.get_relevance_keywords()
        
        # Get filtering settings
        min_score = self.filtering_settings.get("min_relevance_score", 1)
        
        scored_articles = []
        for article in articles:
            score = 0
            text = (article.get("title", "") + " " + article.get("snippet", "")).lower()
            
            for keyword in high_value_keywords:
                if keyword in text:
                    score += 1
            
            if score >= min_score:  # Use configurable minimum score
                article["relevance_score"] = score
                scored_articles.append(article)
        
        # Sort by relevance score and return top articles
        scored_articles.sort(key=lambda x: x["relevance_score"], reverse=True)
        return scored_articles[:Config.MAX_ARTICLES]