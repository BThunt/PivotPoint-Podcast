#!/usr/bin/env python3
"""
PivotPoint Podcast

A clean, modular implementation for generating daily cybersecurity podcasts.
"""

import sys
import logging
import argparse
from pathlib import Path

# Add the current directory to Python path for imports
sys.path.append(str(Path(__file__).parent))

from config.settings import Config
from modules.news_collector import NewsCollector
from modules.content_generator import ContentGenerator
from modules.audio_generator import AudioGenerator
from modules.article_analyzer import ArticleAnalyzer
from modules.article_enhancer import ArticleEnhancer
from utils.helpers import setup_logging, save_json, create_unique_output_directory

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description='Generate cybersecurity podcast with configurable search options')
    
    parser.add_argument('search_mode', nargs='?', default=None,
                       choices=['basic_keywords', 'google_dorks', 'both'],
                       help='Search mode to use (overrides config file settings)')
    
    parser.add_argument('--no-filtering', action='store_true',
                       help='Disable relevance filtering (only use max_articles_per_query)')
    
    parser.add_argument('--no-enhancement', action='store_true',
                       help='Disable article enhancement (use original Serper snippets)')
    
    parser.add_argument('--model', type=str, default='openai', choices=['openai', 'gemini', 'gemini-flash'],
                       help='Choose AI model: openai (GPT-4), gemini (Gemini 2.5 Pro), or gemini-flash (Gemini 2.5 Flash Lite)')
    
    parser.add_argument('--tts', type=str, default=None, choices=['openai', 'elevenlabs'],
                       help='Choose TTS provider: openai (OpenAI TTS) or elevenlabs (ElevenLabs TTS)')
    
    parser.add_argument('--max-articles', type=int, default=None,
                       help='Override max articles per query setting')
    
    parser.add_argument('--days-back', type=int, default=None,
                       help='Override days back for news search')
    
    return parser.parse_args()

def configure_search_modes(args):
    """Configure search modes based on command-line arguments."""
    from utils.search_config_loader import search_config_loader
    
    if args.search_mode:
        # Override configuration based on command-line argument
        params = search_config_loader.load_parameters()
        
        if args.search_mode == 'basic_keywords':
            params['search_modes']['basic_keywords']['enabled'] = True
            params['search_modes']['google_dorks']['enabled'] = False
        elif args.search_mode == 'google_dorks':
            params['search_modes']['basic_keywords']['enabled'] = False
            params['search_modes']['google_dorks']['enabled'] = True
        elif args.search_mode == 'both':
            params['search_modes']['basic_keywords']['enabled'] = True
            params['search_modes']['google_dorks']['enabled'] = True
        
        # Update the cached parameters
        search_config_loader._parameters = params
    
    return search_config_loader.get_active_search_queries()

def main(args=None):
    """Main execution function."""
    # Parse command-line arguments if not provided
    if args is None:
        args = parse_arguments()
    
    # Setup logging
    logger = setup_logging()
    logger.info("Starting PivotPoint Podcast Generator")
    
    # Log search configuration
    if args.search_mode:
        logger.info(f"Using search mode: {args.search_mode}")
    if args.no_filtering:
        logger.info("Relevance filtering disabled")
    if args.no_enhancement:
        logger.info("Article enhancement disabled")
    if args.max_articles:
        logger.info(f"Max articles override: {args.max_articles}")
    if args.tts:
        logger.info(f"TTS provider override: {args.tts}")
    
    try:
        # Set the selected model
        Config.set_selected_model(args.model)
        logger.info(f"Using AI model: {args.model}")
        
        # Set the TTS provider if specified
        if args.tts:
            Config.set_tts_provider(args.tts)
            logger.info(f"Using TTS provider: {args.tts}")
        else:
            logger.info(f"Using default TTS provider: {Config.TTS_PROVIDER}")
        
        # Create unique output directory for this run
        output_dir = create_unique_output_directory("podcast_run")
        Config.set_output_directory(output_dir)
        logger.info(f"Created output directory: {output_dir}")
        
        # Configure search modes based on arguments
        active_queries = configure_search_modes(args)
        logger.info(f"Active search queries: {len(active_queries)} queries")
        
        # Validate configuration
        Config.validate()
        logger.info("Configuration validated successfully")
        
        # Initialize modules with custom settings
        news_collector = NewsCollector()
        
        # Apply command-line overrides to news collector
        if args.max_articles:
            news_collector.filtering_settings['max_articles_per_query'] = args.max_articles
            news_collector.filtering_settings['max_articles_per_category'] = args.max_articles
        if args.days_back:
            news_collector.date_settings['default_days_back'] = args.days_back
        
        content_generator = ContentGenerator()
        
        # Initialize audio generator with TTS provider override if specified
        tts_provider = args.tts if args.tts else None
        audio_generator = AudioGenerator(tts_provider=tts_provider)
        
        article_analyzer = ArticleAnalyzer()
        article_enhancer = ArticleEnhancer()
        
        # Step 1: Collect news
        logger.info("Step 1: Collecting cybersecurity news...")
        all_articles = news_collector.collect_daily_news()
        
        if not all_articles:
            logger.warning("No articles found. Proceeding with fallback content.")
            relevant_articles = []
        else:
            if args.no_filtering:
                # Skip relevance filtering, use all collected articles (already limited per category)
                relevant_articles = all_articles
                logger.info(f"No filtering applied. Using all {len(relevant_articles)} articles from categories")
            else:
                # Filter for most relevant articles
                relevant_articles = news_collector.filter_relevant_articles(all_articles)
                logger.info(f"Selected {len(relevant_articles)} relevant articles")
        
        # Save sources for reference
        save_json(relevant_articles, Config.get_sources_file())
        logger.info(f"Saved article sources to {Config.get_sources_file()}")
        
        # Step 2: Enhance articles with GPT-generated summaries (if enabled)
        if args.no_enhancement:
            logger.info("Step 2: Skipping article enhancement (using original snippets)")
            enhanced_articles = relevant_articles
            enhanced_articles_file = None
        else:
            logger.info("Step 2: Enhancing articles with GPT-generated summaries...")
            enhanced_articles = article_enhancer.enhance_articles(relevant_articles)
            
            # Save enhanced articles for reference
            from utils.helpers import get_output_file_path
            enhanced_articles_file = get_output_file_path(Config.OUTPUT_DIR, "articles_summarised.json")
            article_enhancer.save_enhanced_articles(enhanced_articles, enhanced_articles_file)
            logger.info(f"Saved enhanced articles to {enhanced_articles_file}")
        
        # Step 3: Analyze articles to select most interesting by category
        logger.info("Step 3: Analyzing articles to select most interesting by category...")
        analysis_result, selected_articles = article_analyzer.analyze_articles_by_category(enhanced_articles)
        
        # Save analysis to file
        from utils.helpers import get_output_file_path
        analysis_file = get_output_file_path(Config.OUTPUT_DIR, "gpt-article-analysis.txt")
        article_analyzer.save_analysis_to_file(analysis_result, analysis_file)
        logger.info(f"Saved article analysis to {analysis_file}")
        
        # Use selected articles for podcast generation instead of all articles
        if selected_articles:
            podcast_articles = selected_articles
            logger.info(f"Using {len(selected_articles)} GPT-selected articles for podcast generation")
        else:
            # Fallback to enhanced articles if selection failed
            podcast_articles = enhanced_articles
            logger.warning("No articles selected by GPT analysis, using enhanced articles as fallback")
        
        # Step 4: Generate podcast script
        logger.info("Step 4: Generating podcast script...")
        script = content_generator.create_podcast_script(podcast_articles)
        
        # Save transcript
        with open(Config.get_transcript_file(), 'w', encoding='utf-8') as f:
            f.write(script)
        logger.info(f"Saved transcript to {Config.get_transcript_file()}")
        
        # Log article summary for reference
        if podcast_articles:
            article_summary = content_generator.summarize_articles(podcast_articles)
            logger.info(f"Selected articles used for podcast:\n{article_summary}")
        
        # Step 5: Generate audio
        logger.info(f"Step 5: Generating audio using {audio_generator.get_tts_provider()} TTS...")
        audio_file = audio_generator.generate_audio_from_long_text(script)
        logger.info(f"Generated audio file: {audio_file}")
        
        # Success summary
        logger.info("=" * 50)
        logger.info("PODCAST GENERATION COMPLETE")
        logger.info("=" * 50)
        logger.info(f"Output directory: {Config.OUTPUT_DIR}")
        logger.info(f"Transcript: {Config.get_transcript_file()}")
        logger.info(f"Audio: {audio_file}")
        logger.info(f"Sources: {Config.get_sources_file()}")
        if enhanced_articles_file:
            logger.info(f"Enhanced Articles: {enhanced_articles_file}")
        logger.info(f"Article Analysis: {analysis_file}")
        logger.info(f"Total articles collected: {len(relevant_articles)}")
        if not args.no_enhancement:
            enhanced_count = sum(1 for a in enhanced_articles if a.get('enhanced', False))
            logger.info(f"Enhanced articles: {enhanced_count}/{len(enhanced_articles)}")
        logger.info(f"Selected articles used for podcast: {len(podcast_articles)}")
        
        return True
        
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        logger.error("Please check your environment variables and API keys")
        return False
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.error("Podcast generation failed")
        return False

def check_dependencies():
    """Check if required packages are installed."""
    required_packages = [
        ('openai', 'openai'),
        ('requests', 'requests'),
        ('python-dotenv', 'dotenv')
    ]
    
    missing_packages = []
    for package_name, import_name in required_packages:
        try:
            __import__(import_name)
        except ImportError:
            missing_packages.append(package_name)
    
    if missing_packages:
        print("Missing required packages:")
        for package in missing_packages:
            print(f"  - {package}")
        print("\nInstall them with:")
        print(f"pip install {' '.join(missing_packages)}")
        return False
    
    return True

if __name__ == "__main__":
    # Check dependencies first
    if not check_dependencies():
        sys.exit(1)
    
    # Parse arguments and run main function
    args = parse_arguments()
    success = main(args)
    sys.exit(0 if success else 1)