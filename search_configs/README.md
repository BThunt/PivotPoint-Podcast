# Search Configurations Directory

This directory contains all the search configurations used by the OpenAI Podcast Generator for collecting cybersecurity news. Each configuration is stored in separate files for easy editing and management.

## Available Configuration Files

### Search Query Files

- **`basic-keywords.txt`** - Simple keyword-based search terms for cybersecurity news
- **`google-dorks.txt`** - Advanced Google Dork search queries for more targeted results
- **`relevance-keywords.txt`** - Keywords used to score and filter articles for relevance

### Configuration Files

- **`search-parameters.json`** - Main configuration file containing API settings, search modes, and filtering parameters

## Configuration File Details

### basic-keywords.txt
Contains simple search terms, one per line. These are basic keyword searches that will be combined with date filters.

Example:
```
cybersecurity breach
data breach
ransomware attack
```

### google-dorks.txt
Contains categorized Google search operators for comprehensive cybersecurity news coverage. Each non-comment line represents a category-specific search query. The system treats each query as a separate category and limits results per category.

**Current Categories:**
1. **APTs & Cyber-Espionage**: Advanced persistent threats and espionage campaigns
2. **Arrests & Cybercrime**: Law enforcement actions and cybercrime takedowns
3. **Breaches & Incidents**: Data breaches and security incidents
4. **Cybersecurity IPOs**: Public offerings and stock market debuts
5. **Cybersecurity Funding**: Investment rounds and venture capital
6. **Cybersecurity M&A**: Mergers and acquisitions

Example:
```
# APTs & Cyber-Espionage
("advanced persistent threat" OR APT OR "cyber espionage") (campaign OR operation OR group)
```

### relevance-keywords.txt
Contains keywords used to score articles for relevance. Articles containing these keywords get higher relevance scores.

Example:
```
breach
ransomware
vulnerability
zero-day
```

### search-parameters.json
Main configuration file with the following sections:

#### API Settings
- `base_url`: SerperAPI endpoint
- `timeout`: Request timeout in seconds
- `num_results`: Number of results per query
- `geographic_location`: Geographic filter (e.g., "us")
- `language`: Language filter (e.g., "en")

#### Search Modes
- `basic_keywords`: Enable/disable basic keyword searches
- `google_dorks`: Enable/disable Google Dork searches

#### Filtering Settings
- `relevance_keywords_file`: File containing relevance keywords
- `min_relevance_score`: Minimum score for article inclusion
- `max_articles_per_query`: Maximum articles per search query

## How to Edit Configurations

### Enabling/Disabling Search Modes

Edit `search-parameters.json` to enable or disable different search modes:

```json
"search_modes": {
  "basic_keywords": {
    "enabled": true,
    "description": "Simple keyword-based searches"
  },
  "google_dorks": {
    "enabled": false,
    "description": "Advanced Google Dork searches"
  }
}
```

### Adding New Keywords

1. **Basic Keywords**: Add new lines to `basic-keywords.txt`
2. **Google Dorks**: Add new search queries to `google-dorks.txt`
3. **Relevance Keywords**: Add new scoring keywords to `relevance-keywords.txt`

### Modifying API Settings

Edit the `api_settings` section in `search-parameters.json`:

```json
"api_settings": {
  "base_url": "https://google.serper.dev/news",
  "timeout": 10,
  "num_results": 10,
  "geographic_location": "us",
  "language": "en"
}
```

### Adjusting Filtering

Modify the `filtering` section to change how articles are filtered:

```json
"filtering": {
  "min_relevance_score": 1,
  "max_articles_per_query": 10,
  "duplicate_detection": "url_based"
}
```

## Usage in Code

The search configurations are loaded automatically via the `SearchConfigLoader`:

```python
from utils.search_config_loader import search_config_loader

# Get active search queries (based on enabled modes)
queries = search_config_loader.get_active_search_queries()

# Get specific configuration lists
basic_keywords = search_config_loader.get_basic_keywords()
google_dorks = search_config_loader.get_google_dorks()
relevance_keywords = search_config_loader.get_relevance_keywords()

# Get configuration settings
api_settings = search_config_loader.get_api_settings()
filtering_settings = search_config_loader.get_filtering_settings()
```

## Best Practices

1. **Testing**: Test configuration changes with sample searches before production use
2. **Backup**: Keep backups of working configurations before making major changes
3. **Documentation**: Document any custom search queries or special configurations
4. **Performance**: Monitor search performance and adjust timeouts/limits as needed
5. **Relevance**: Regularly review and update relevance keywords based on results

## Google Dorks Tips

When creating Google Dorks, consider:

- **Site-specific searches**: `site:domain.com "keyword"`
- **Exact phrases**: Use quotes for exact matches
- **Boolean operators**: Use OR, AND, NOT
- **Wildcards**: Use * for unknown words
- **Date ranges**: Combine with date filters for recent content
- **File types**: `filetype:pdf "cybersecurity"`

## Command-Line Usage

You can now override search configurations at runtime using command-line arguments:

### Basic Usage
```bash
# Use default configuration (from search-parameters.json)
python main.py

# Use only Google Dorks
python main.py google_dorks

# Use only basic keywords
python main.py basic_keywords

# Use both search modes
python main.py both
```

### Advanced Options
```bash
# Disable relevance filtering (only use max articles limit)
python main.py google_dorks --no-filtering

# Override max articles per query
python main.py basic_keywords --max-articles 15

# Override days back for news search
python main.py google_dorks --days-back 3

# Combine multiple options
python main.py google_dorks --no-filtering --max-articles 5 --days-back 2
```

### Command-Line Arguments
- `search_mode`: Choose `basic_keywords`, `google_dorks`, or `both`
- `--no-filtering`: Skip relevance filtering, only limit by max articles
- `--max-articles N`: Override maximum articles per query
- `--days-back N`: Override how many days back to search

## Troubleshooting

- **No results**: Check if search terms are too specific
- **Too many results**: Increase relevance score threshold or use `--max-articles`
- **API errors**: Verify API settings and rate limits
- **Duplicate articles**: Ensure duplicate detection is enabled
- **Performance issues**: Reduce number of search queries or results per query
- **Google Dorks not working**: Ensure queries in `google-dorks.txt` are not commented out