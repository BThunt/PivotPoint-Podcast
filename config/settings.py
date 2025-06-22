import os
from dotenv import load_dotenv

# Load environment variables from .env file in project directory
load_dotenv()

class Config:
    """Configuration settings for the podcast generator."""
    
    # API Keys
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPEN_ROUTER_API_KEY = os.getenv("OPEN_ROUTER")
    SERPER_API_KEY = os.getenv("SERPER_API_KEY")
    ELEVEN_LABS_API_KEY = os.getenv("ELEVEN_LABS_API_KEY")
    
    # Model Configuration
    SELECTED_MODEL = "openai"  # Default model, can be overridden at runtime
    
    # Audio Settings
    VOICE_ID = os.getenv("VOICE_ID", "alloy")
    AUDIO_FORMAT = os.getenv("AUDIO_FORMAT", "mp3")
    SPEAKING_SPEED = float(os.getenv("SPEAKING_SPEED", "1.0"))
    
    # TTS Provider Settings
    TTS_PROVIDER = os.getenv("TTS_PROVIDER", "openai")  # "openai" or "elevenlabs"
    
    # ElevenLabs Settings
    ELEVEN_LABS_VOICE_ID = os.getenv("ELEVEN_LABS_VOICE_ID", "your-voice-id-here")
    ELEVEN_LABS_MODEL = os.getenv("ELEVEN_LABS_MODEL", "eleven_multilingual_v2")
    ELEVEN_LABS_STABILITY = float(os.getenv("ELEVEN_LABS_STABILITY", "0.5"))
    ELEVEN_LABS_SIMILARITY_BOOST = float(os.getenv("ELEVEN_LABS_SIMILARITY_BOOST", "0.85"))
    ELEVEN_LABS_STYLE = float(os.getenv("ELEVEN_LABS_STYLE", "0.0"))
    ELEVEN_LABS_USE_SPEAKER_BOOST = os.getenv("ELEVEN_LABS_USE_SPEAKER_BOOST", "true").lower() == "true"
    ELEVEN_LABS_SPEED = float(os.getenv("ELEVEN_LABS_SPEED", "0.9"))
    
    # Content Settings
    MAX_ARTICLES = int(os.getenv("MAX_ARTICLES", "5"))
    PODCAST_LENGTH_MINUTES = int(os.getenv("PODCAST_LENGTH_MINUTES", "5"))
    
    # Search Configuration (now loaded from external files)
    @classmethod
    def get_search_keywords(cls):
        """Get search keywords from external configuration."""
        from utils.search_config_loader import search_config_loader
        return search_config_loader.get_active_search_queries()
    
    # Legacy property for backward compatibility
    @property
    def CYBERSECURITY_KEYWORDS(self):
        return self.get_search_keywords()
    
    # Output Files (base names - will be combined with output directory)
    TRANSCRIPT_FILENAME = "daily_briefing.txt"
    AUDIO_FILENAME = f"daily_briefing.{AUDIO_FORMAT}"
    SOURCES_FILENAME = "sources.json"
    
    # Dynamic output directory (set at runtime)
    OUTPUT_DIR = None
    
    @classmethod
    def set_output_directory(cls, output_dir: str):
        """Set the output directory for this run."""
        cls.OUTPUT_DIR = output_dir
    
    @classmethod
    def set_selected_model(cls, model: str):
        """Set the selected model for this run."""
        cls.SELECTED_MODEL = model
    
    @classmethod
    def get_transcript_file(cls) -> str:
        """Get the full path for the transcript file."""
        if cls.OUTPUT_DIR:
            from pathlib import Path
            return str(Path(cls.OUTPUT_DIR) / cls.TRANSCRIPT_FILENAME)
        return cls.TRANSCRIPT_FILENAME
    
    @classmethod
    def get_audio_file(cls) -> str:
        """Get the full path for the audio file."""
        if cls.OUTPUT_DIR:
            from pathlib import Path
            return str(Path(cls.OUTPUT_DIR) / cls.AUDIO_FILENAME)
        return cls.AUDIO_FILENAME
    
    @classmethod
    def get_sources_file(cls) -> str:
        """Get the full path for the sources file."""
        if cls.OUTPUT_DIR:
            from pathlib import Path
            return str(Path(cls.OUTPUT_DIR) / cls.SOURCES_FILENAME)
        return cls.SOURCES_FILENAME
    
    # Legacy properties for backward compatibility
    @property
    def TRANSCRIPT_FILE(self):
        return self.get_transcript_file()
    
    @property
    def AUDIO_FILE(self):
        return self.get_audio_file()
    
    @property
    def SOURCES_FILE(self):
        return self.get_sources_file()
    
    @classmethod
    def validate(cls):
        """Validate that required configuration is present."""
        if cls.SELECTED_MODEL == "gemini":
            if not cls.OPEN_ROUTER_API_KEY:
                raise ValueError("OPEN_ROUTER API key is required when using Gemini model")
        else:
            if not cls.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY is required when using OpenAI model")
        
        # Validate TTS provider requirements
        if cls.TTS_PROVIDER == "elevenlabs":
            if not cls.ELEVEN_LABS_API_KEY:
                raise ValueError("ELEVEN_LABS_API_KEY is required when using ElevenLabs TTS")
        elif cls.TTS_PROVIDER == "openai":
            if not cls.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY is required when using OpenAI TTS")
        
        if not cls.SERPER_API_KEY:
            raise ValueError("SERPER_API_KEY is required")
        return True
    
    @classmethod
    def set_tts_provider(cls, provider: str):
        """Set the TTS provider for this run."""
        if provider not in ["openai", "elevenlabs"]:
            raise ValueError("TTS provider must be 'openai' or 'elevenlabs'")
        cls.TTS_PROVIDER = provider