import openai
import logging
from pathlib import Path

from config.settings import Config
from utils.helpers import clean_text_for_audio

logger = logging.getLogger(__name__)

class AudioGenerator:
    """Generates audio from text using OpenAI's TTS or ElevenLabs TTS."""
    
    def __init__(self, tts_provider: str = None):
        self.tts_provider = tts_provider or Config.TTS_PROVIDER
        self.voice_id = Config.VOICE_ID
        self.audio_format = Config.AUDIO_FORMAT
        self.speaking_speed = Config.SPEAKING_SPEED
        
        # Initialize the appropriate TTS provider
        if self.tts_provider == "elevenlabs":
            from modules.elevenlabs_tts import ElevenLabsTTS
            self.elevenlabs_tts = ElevenLabsTTS()
            logger.info("Initialized AudioGenerator with ElevenLabs TTS")
        else:
            openai.api_key = Config.OPENAI_API_KEY
            self.elevenlabs_tts = None
            logger.info("Initialized AudioGenerator with OpenAI TTS")
    
    def generate_audio(self, text: str, output_file: str = None) -> str:
        """Generate audio from text and save to file."""
        if self.tts_provider == "elevenlabs":
            return self.elevenlabs_tts.generate_audio(text, output_file)
        else:
            return self._generate_openai_audio(text, output_file)
    
    def _generate_openai_audio(self, text: str, output_file: str = None) -> str:
        """Generate audio from text using OpenAI TTS."""
        if output_file is None:
            output_file = Config.get_audio_file()
        
        # Clean text for better audio generation
        clean_text = clean_text_for_audio(text)
        
        if not clean_text.strip():
            logger.error("No text provided for audio generation")
            raise ValueError("Text cannot be empty")
        
        try:
            logger.info(f"Generating audio with OpenAI voice '{self.voice_id}'")
            logger.info(f"Text length: {len(clean_text)} characters")
            
            # Prepare TTS parameters
            tts_params = {
                "model": "tts-1",
                "voice": self.voice_id,
                "input": clean_text
            }
            
            # Add speed if configured
            if self.speaking_speed and self.speaking_speed != 1.0:
                tts_params["speed"] = self.speaking_speed
                logger.info(f"Using speaking speed: {self.speaking_speed}")
            
            # Generate audio
            response = openai.audio.speech.create(**tts_params)
            
            # Save to file
            output_path = Path(output_file)
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"Audio saved to: {output_path.absolute()}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Error generating audio: {str(e)}")
            raise
    
    def validate_text_length(self, text: str) -> bool:
        """Validate that text is within TTS limits."""
        if self.tts_provider == "elevenlabs":
            # ElevenLabs has a 5000 character limit
            max_chars = 5000
        else:
            # OpenAI TTS has a 4096 character limit
            max_chars = 4096
        
        if len(text) > max_chars:
            logger.warning(f"Text length ({len(text)}) exceeds {self.tts_provider} TTS limit ({max_chars})")
            return False
        
        return True
    
    def split_long_text(self, text: str, max_chars: int = None) -> list:
        """Split long text into chunks for TTS processing."""
        if max_chars is None:
            max_chars = 5000 if self.tts_provider == "elevenlabs" else 4000
        
        if len(text) <= max_chars:
            return [text]
        
        chunks = []
        sentences = text.split('. ')
        current_chunk = ""
        
        for sentence in sentences:
            # Check if adding this sentence would exceed the limit
            if len(current_chunk + sentence + '. ') <= max_chars:
                current_chunk += sentence + '. '
            else:
                # Save current chunk and start a new one
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + '. '
        
        # Add the last chunk
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        logger.info(f"Split text into {len(chunks)} chunks for {self.tts_provider}")
        return chunks
    
    def generate_audio_from_long_text(self, text: str, output_file: str = None) -> str:
        """Generate audio from potentially long text by splitting if necessary."""
        # For ElevenLabs, delegate to its own chunking logic
        if self.tts_provider == "elevenlabs":
            return self.elevenlabs_tts.generate_audio(text, output_file)
        
        # For OpenAI, use the existing chunking logic
        if self.validate_text_length(text):
            return self.generate_audio(text, output_file)
        
        # Split text and generate multiple audio files
        chunks = self.split_long_text(text)
        audio_files = []
        
        logger.info(f"Generating {len(chunks)} OpenAI audio chunks for long text")
        
        for i, chunk in enumerate(chunks):
            if Config.OUTPUT_DIR:
                from pathlib import Path
                chunk_file = str(Path(Config.OUTPUT_DIR) / f"temp_audio_chunk_{i}.{self.audio_format}")
            else:
                chunk_file = f"temp_audio_chunk_{i}.{self.audio_format}"
            
            logger.info(f"Generating OpenAI chunk {i+1}/{len(chunks)}")
            audio_files.append(self.generate_audio(chunk, chunk_file))
        
        # Combine all chunks into final audio file
        logger.info("All OpenAI chunks generated. Combining into final audio file...")
        final_audio_file = self._combine_audio_chunks(audio_files, output_file)
        
        # Only clean up temporary chunk files if combining was successful
        if final_audio_file and Path(final_audio_file).exists():
            logger.info("Combining successful. Cleaning up temporary chunk files...")
            self._cleanup_chunk_files(audio_files)
        else:
            logger.warning("Combining failed. Keeping chunk files for manual recovery.")
            logger.info(f"Chunk files available: {[Path(f).name for f in audio_files]}")
        
        return final_audio_file
    
    def get_supported_voices(self) -> list:
        """Get list of supported voice IDs."""
        if self.tts_provider == "elevenlabs":
            return self.elevenlabs_tts.get_supported_voices()
        else:
            return ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
    
    def _combine_audio_chunks(self, chunk_files: list, output_file: str = None) -> str:
        """Combine multiple audio chunk files into a single file."""
        if not chunk_files:
            raise ValueError("No chunk files to combine")
        
        if len(chunk_files) == 1:
            # Only one chunk, just rename it
            final_file = output_file or Config.get_audio_file()
            import shutil
            shutil.move(chunk_files[0], final_file)
            logger.info(f"Single chunk moved to: {final_file}")
            return final_file
        
        # Use simple concatenation directly (more reliable)
        return self._simple_combine_chunks(chunk_files, output_file)
    
    def _simple_combine_chunks(self, chunk_files: list, output_file: str = None) -> str:
        """Simple method to combine chunks by concatenating bytes."""
        # Determine the final output file path
        if output_file is None:
            # Use the same directory as the chunks with the default filename
            chunk_dir = Path(chunk_files[0]).parent
            final_file = str(chunk_dir / "daily_briefing.mp3")
        else:
            final_file = output_file
        
        logger.info(f"Combining {len(chunk_files)} chunks into: {final_file}")
        
        try:
            with open(final_file, 'wb') as outfile:
                for i, chunk_file in enumerate(chunk_files):
                    logger.info(f"Appending chunk {i+1}/{len(chunk_files)}: {Path(chunk_file).name}")
                    with open(chunk_file, 'rb') as infile:
                        # Skip MP3 header for subsequent files to reduce glitches
                        if i > 0:
                            infile.read(1024)  # Skip first 1024 bytes
                        outfile.write(infile.read())
            
            logger.info(f"✓ Successfully combined {len(chunk_files)} chunks: {final_file}")
            return final_file
            
        except Exception as e:
            logger.error(f"Error in chunk combination: {e}")
            # Return the first chunk as last resort
            logger.warning(f"Falling back to first chunk: {chunk_files[0]}")
            return chunk_files[0]
    
    def _cleanup_chunk_files(self, chunk_files: list):
        """Clean up temporary chunk files after combining."""
        for chunk_file in chunk_files:
            try:
                Path(chunk_file).unlink()
                logger.debug(f"Deleted temporary chunk: {Path(chunk_file).name}")
            except Exception as e:
                logger.warning(f"Could not delete chunk file {chunk_file}: {e}")
        
        logger.info(f"Cleaned up {len(chunk_files)} temporary chunk files")
    
    def get_supported_formats(self) -> list:
        """Get list of supported audio formats."""
        if self.tts_provider == "elevenlabs":
            return ["mp3"]  # ElevenLabs primarily supports MP3
        else:
            return ["mp3", "opus", "aac", "flac"]
    
    def get_tts_provider(self) -> str:
        """Get the current TTS provider."""
        return self.tts_provider
    
    def set_tts_provider(self, provider: str):
        """Set the TTS provider (openai or elevenlabs)."""
        if provider not in ["openai", "elevenlabs"]:
            raise ValueError("TTS provider must be 'openai' or 'elevenlabs'")
        
        if provider != self.tts_provider:
            self.tts_provider = provider
            if provider == "elevenlabs":
                from modules.elevenlabs_tts import ElevenLabsTTS
                self.elevenlabs_tts = ElevenLabsTTS()
                logger.info("Switched to ElevenLabs TTS")
            else:
                self.elevenlabs_tts = None
                logger.info("Switched to OpenAI TTS")