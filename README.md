# PivotPoint Podcast

An AI-powered cybersecurity podcast generator that creates daily briefings using OpenAI GPT models, web search, and text-to-speech synthesis.

## Features

- 🔍 **Smart Article Collection** - Automated web search using configurable keywords and Google dorks
- 🤖 **AI-Enhanced Content** - GPT-powered article analysis and podcast script generation
- 🎙️ **Multi-Model Support** - OpenAI GPT-4, Gemini 2.5 Pro, and Gemini Flash Lite
- 🎤 **Dual TTS Options** - OpenAI TTS (default) or ElevenLabs for premium quality
- 💾 **Intelligent Caching** - Avoids re-processing articles and optimizes API usage
- 🎵 **Audio Processing** - Automatic chunking and combining for long-form content
- ⚙️ **Flexible Configuration** - Multiple search strategies and customizable settings

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env` and add your API keys:
```bash
cp .env.example .env
```

Edit `.env` with your credentials:
```bash
# Required
OPENAI_API_KEY=your-openai-api-key-here
SERPER_API_KEY=your-serper-api-key-here

# Optional (for advanced features)
OPEN_ROUTER=your-openrouter-key-here          # For Gemini models
ELEVEN_LABS_API_KEY=your-elevenlabs-key-here  # For premium TTS
ELEVEN_LABS_VOICE_ID=your-voice-id-here       # Your preferred voice
```

### 3. Run the Generator
```bash
# Basic usage with OpenAI TTS
python main.py google_dorks

# Use ElevenLabs for higher quality audio
python main.py --tts elevenlabs google_dorks

# Use Gemini models for content generation
python main.py --model gemini google_dorks
```

## Search Configurations

The project includes several pre-configured search strategies in `search_configs/`:

- **`google_dorks`** - Advanced search operators for targeted results
- **`basic_keywords`** - Simple keyword-based searches
- **`relevance_keywords`** - Curated high-relevance terms

## API Keys Setup

### Required APIs

**OpenAI API** (Required)
1. Visit [OpenAI Platform](https://platform.openai.com/api-keys)
2. Create account and generate API key
3. Add billing information for usage

**Serper API** (Required)
1. Visit [Serper.dev](https://serper.dev/)
2. Sign up for free account (2,500 free searches)
3. Copy API key from dashboard

### Optional APIs

**OpenRouter** (For Gemini Models)
1. Visit [OpenRouter.ai](https://openrouter.ai/)
2. Create account and add credits
3. Enables access to Google's Gemini models

**ElevenLabs** (Premium TTS)
1. Visit [ElevenLabs.io](https://elevenlabs.io/)
2. Create account (10,000 free characters monthly)
3. Get API key and voice ID from profile

## Project Structure

```
PivotPoint Podcast/
├── main.py                 # Application entry point
├── requirements.txt        # Python dependencies
├── .env.example           # Environment variables template
├── .gitignore            # Git ignore rules
├── config/               # Configuration settings
├── modules/              # Core application modules
│   ├── audio_generator.py    # TTS and audio processing
│   ├── content_generator.py  # AI script generation
│   ├── news_collector.py     # Web search and article collection
│   ├── article_enhancer.py   # Full article content extraction
│   ├── article_analyzer.py   # AI article analysis
│   └── elevenlabs_tts.py     # ElevenLabs TTS integration
├── prompts/              # AI prompt templates
├── search_configs/       # Search strategy configurations
└── utils/               # Helper functions and utilities
```

## Command Line Options

```bash
python main.py [OPTIONS] SEARCH_CONFIG

Options:
  --model MODEL         AI model: openai, gemini, gemini-flash (default: openai)
  --tts PROVIDER        TTS provider: openai, elevenlabs (default: openai)
  --max-articles N      Maximum articles to process (default: 5)
  --output-dir DIR      Custom output directory

Search Configs:
  google_dorks          Advanced search operators (recommended)
  basic_keywords        Simple keyword searches
  relevance_keywords    High-relevance cybersecurity terms
```

## Output Files

Each run creates a timestamped directory containing:
- `daily_briefing.txt` - Generated podcast transcript
- `daily_briefing.mp3` - Audio file (MP3 format)
- `sources.json` - Article sources and metadata
- `articles_summarised.json` - Enhanced article summaries
- `cache/` - Cached article content (if applicable)

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | OpenAI API key for GPT models and TTS |
| `SERPER_API_KEY` | Yes | Serper API key for web search |
| `OPEN_ROUTER` | No | OpenRouter key for Gemini model access |
| `ELEVEN_LABS_API_KEY` | No | ElevenLabs API key for premium TTS |
| `ELEVEN_LABS_VOICE_ID` | No | Your preferred ElevenLabs voice ID |
| `TTS_PROVIDER` | No | Default TTS provider (openai/elevenlabs) |
| `VOICE_ID` | No | OpenAI voice selection (alloy, echo, fable, onyx, nova, shimmer) |
| `MAX_ARTICLES` | No | Maximum articles to process (default: 5) |
| `PODCAST_LENGTH_MINUTES` | No | Target podcast length (default: 5) |

### Search Configuration

Customize search behavior by editing files in `search_configs/`:
- Modify keyword lists for different focus areas
- Adjust search parameters in `search-parameters.json`
- Create custom search strategies

## Troubleshooting

**Common Issues:**

1. **API Key Errors** - Ensure all required keys are set in `.env`
2. **Rate Limits** - Reduce `MAX_ARTICLES` or add delays between requests
3. **Audio Quality** - Try ElevenLabs TTS for better voice quality
4. **Long Processing** - Use `gemini-flash` model for faster generation

**Debug Mode:**
```bash
# Enable verbose logging
export LOG_LEVEL=DEBUG
python main.py google_dorks
```

## License

This project is open source. Please comply with the terms of service for all API providers used.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

For questions or support, please open an issue on GitHub.
