import re
import json
import logging
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any
from pathlib import Path

def setup_logging() -> logging.Logger:
    """Set up logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)

def get_date_range(days_back: int = 1) -> tuple:
    """Get date range for news search."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    return start_date, end_date

def format_date_for_search(date: datetime) -> str:
    """Format date for search API."""
    return date.strftime("%Y-%m-%d")

def clean_text_for_audio(text: str) -> str:
    """Clean text for better audio generation."""
    # Remove URLs
    text = re.sub(r'http[s]?://\S+', '', text)
    
    # Remove markdown formatting
    text = re.sub(r'[#*_`]', '', text)
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove special characters that might cause TTS issues
    text = re.sub(r'[^\w\s.,!?;:\-()]', '', text)
    
    return text.strip()

def save_json(data: Any, filepath: str) -> None:
    """Save data to JSON file."""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_json(filepath: str) -> Any:
    """Load data from JSON file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def truncate_text(text: str, max_length: int = 4000) -> str:
    """Truncate text to fit within token limits."""
    if len(text) <= max_length:
        return text
    
    # Try to truncate at sentence boundary
    sentences = text.split('. ')
    truncated = ""
    for sentence in sentences:
        if len(truncated + sentence + '. ') <= max_length:
            truncated += sentence + '. '
        else:
            break
    
    return truncated.strip()

def estimate_reading_time(text: str, words_per_minute: int = 150) -> float:
    """Estimate reading time in minutes."""
    word_count = len(text.split())
    return word_count / words_per_minute

def format_podcast_intro() -> str:
    """Generate podcast intro with current date."""
    from utils.prompt_loader import prompt_loader
    today = datetime.now().strftime("%B %d, %Y")
    return prompt_loader.format_prompt("podcast-intro", date=today)

def format_podcast_outro() -> str:
    """Generate podcast outro."""
    from utils.prompt_loader import prompt_loader
    return prompt_loader.load_prompt("podcast-outro")

def create_unique_output_directory(base_name: str = "podcast_run") -> str:
    """Create a unique directory for this run's output files."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    directory_name = f"{base_name}_{timestamp}"
    
    # Create the directory path
    output_dir = Path(directory_name)
    
    # Handle potential collisions (though very unlikely with timestamp)
    counter = 1
    original_name = directory_name
    while output_dir.exists():
        directory_name = f"{original_name}_{counter:03d}"
        output_dir = Path(directory_name)
        counter += 1
    
    # Create the directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    return str(output_dir)

def get_output_file_path(output_dir: str, filename: str) -> str:
    """Get the full path for an output file in the specified directory."""
    return str(Path(output_dir) / filename)