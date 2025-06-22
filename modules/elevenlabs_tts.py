import requests
import logging
from pathlib import Path
from typing import List
import time

from config.settings import Config

logger = logging.getLogger(__name__)

class ElevenLabsTTS:
    """ElevenLabs Text-to-Speech generator with chunking support."""
    
    def __init__(self):
        self.api_key = Config.ELEVEN_LABS_API_KEY
        self.voice_id = Config.ELEVEN_LABS_VOICE_ID
        self.model_id = Config.ELEVEN_LABS_MODEL
        self.voice_settings = {
            "stability": Config.ELEVEN_LABS_STABILITY,
            "similarity_boost": Config.ELEVEN_LABS_SIMILARITY_BOOST,
            "style": Config.ELEVEN_LABS_STYLE,
            "use_speaker_boost": Config.ELEVEN_LABS_USE_SPEAKER_BOOST,
            "speed": Config.ELEVEN_LABS_SPEED
        }
        self.max_chars = 1000  # Optimal chunk size for voice quality (ElevenLabs degrades after 1k chars)
        
        if not self.api_key:
            raise ValueError("ELEVEN_LABS_API_KEY is required for ElevenLabs TTS")
    
    def generate_audio(self, text: str, output_file: str = None) -> str:
        """Generate audio from text using ElevenLabs API."""
        if output_file is None:
            output_file = Config.get_audio_file()
        
        # Clean text for better audio generation
        from utils.helpers import clean_text_for_audio
        clean_text = clean_text_for_audio(text)
        
        if not clean_text.strip():
            logger.error("No text provided for audio generation")
            raise ValueError("Text cannot be empty")
        
        # Always use chunking for ElevenLabs to maintain voice quality
        # Voice quality degrades after ~1k characters, so we chunk even short texts
        return self._generate_chunked_audio(clean_text, output_file)
    
    def _generate_single_audio(self, text: str, output_file: str) -> str:
        """Generate audio from a single text chunk."""
        logger.info(f"Generating audio with ElevenLabs voice '{self.voice_id}'")
        logger.info(f"Text length: {len(text)} characters")
        
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}"
        
        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json"
        }
        
        payload = {
            "text": text,
            "model_id": self.model_id,
            "voice_settings": self.voice_settings
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code == 200:
                output_path = Path(output_file)
                with open(output_path, "wb") as f:
                    f.write(response.content)
                
                logger.info(f"✅ Audio saved to: {output_path.absolute()}")
                return str(output_path)
            else:
                logger.error(f"❌ ElevenLabs API Error: {response.status_code} - {response.text}")
                raise Exception(f"ElevenLabs API error: {response.status_code} - {response.text}")
                
        except Exception as e:
            logger.error(f"Error generating audio with ElevenLabs: {str(e)}")
            raise
    
    def _generate_chunked_audio(self, text: str, output_file: str) -> str:
        """Generate audio from text by splitting into optimal chunks for voice quality."""
        chunks = self._split_text_into_chunks(text)
        audio_files = []
        
        logger.info(f"Generating {len(chunks)} ElevenLabs chunks for optimal voice quality ({len(text)} characters)")
        
        for i, chunk in enumerate(chunks):
            if Config.OUTPUT_DIR:
                chunk_file = str(Path(Config.OUTPUT_DIR) / f"temp_elevenlabs_chunk_{i}.mp3")
            else:
                chunk_file = f"temp_elevenlabs_chunk_{i}.mp3"
            
            logger.info(f"Generating ElevenLabs chunk {i+1}/{len(chunks)} ({len(chunk)} chars)")
            
            try:
                audio_files.append(self._generate_single_audio(chunk, chunk_file))
                # Add a small delay between requests to be respectful to the API
                if i < len(chunks) - 1:  # Don't delay after the last chunk
                    time.sleep(1)
            except Exception as e:
                logger.error(f"Failed to generate chunk {i+1}: {str(e)}")
                # Clean up any successfully generated chunks
                self._cleanup_chunk_files(audio_files)
                raise
        
        # Combine all chunks into final audio file
        logger.info("All ElevenLabs chunks generated. Combining into final audio file...")
        final_audio_file = self._combine_audio_chunks(audio_files, output_file)
        
        # Clean up temporary chunk files if combining was successful
        if final_audio_file and Path(final_audio_file).exists():
            logger.info("Combining successful. Cleaning up temporary chunk files...")
            self._cleanup_chunk_files(audio_files)
        else:
            logger.warning("Combining failed. Keeping chunk files for manual recovery.")
            logger.info(f"Chunk files available: {[Path(f).name for f in audio_files]}")
        
        return final_audio_file
    
    def _split_text_into_chunks(self, text: str) -> List[str]:
        """Split text into optimal 1k character chunks for best voice quality."""
        chunks = []
        
        # Split by sentences first for natural breaks
        sentences = text.split('. ')
        current_chunk = ""
        
        for sentence in sentences:
            # Check if adding this sentence would exceed the 1k limit
            test_chunk = current_chunk + sentence + '. '
            if len(test_chunk) <= self.max_chars:
                current_chunk = test_chunk
            else:
                # Save current chunk if it has content
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                
                # Start new chunk with current sentence
                current_chunk = sentence + '. '
                
                # If single sentence is too long, split it by words
                if len(current_chunk) > self.max_chars:
                    words = sentence.split()
                    word_chunk = ""
                    for word in words:
                        if len(word_chunk + word + ' ') <= self.max_chars:
                            word_chunk += word + ' '
                        else:
                            if word_chunk.strip():
                                chunks.append(word_chunk.strip())
                            word_chunk = word + ' '
                    
                    if word_chunk.strip():
                        current_chunk = word_chunk + '. '
                    else:
                        current_chunk = ""
        
        # Add the last chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        # Ensure we always have at least one chunk, even for very short text
        if not chunks and text.strip():
            chunks = [text.strip()]
        
        logger.info(f"Split text into {len(chunks)} optimal chunks for voice quality")
        for i, chunk in enumerate(chunks):
            logger.debug(f"Chunk {i+1}: {len(chunk)} characters")
        
        return chunks
    
    def _combine_audio_chunks(self, chunk_files: List[str], output_file: str = None) -> str:
        """Combine multiple audio chunk files into a single file."""
        if not chunk_files:
            raise ValueError("No chunk files to combine")
        
        if len(chunk_files) == 1:
            # Only one chunk, just rename it
            final_file = output_file or Config.get_audio_file()
            import shutil
            shutil.move(chunk_files[0], final_file)
            logger.info(f"Single ElevenLabs chunk moved to: {final_file}")
            return final_file
        
        # Use simple concatenation for MP3 files
        return self._simple_combine_chunks(chunk_files, output_file)
    
    def _simple_combine_chunks(self, chunk_files: List[str], output_file: str = None) -> str:
        """Simple method to combine chunks by concatenating bytes."""
        # Determine the final output file path
        if output_file is None:
            # Use the same directory as the chunks with the default filename
            chunk_dir = Path(chunk_files[0]).parent
            final_file = str(chunk_dir / "daily_briefing.mp3")
        else:
            final_file = output_file
        
        logger.info(f"Combining {len(chunk_files)} ElevenLabs chunks into: {final_file}")
        
        try:
            with open(final_file, 'wb') as outfile:
                for i, chunk_file in enumerate(chunk_files):
                    logger.info(f"Appending ElevenLabs chunk {i+1}/{len(chunk_files)}: {Path(chunk_file).name}")
                    with open(chunk_file, 'rb') as infile:
                        # Skip MP3 header for subsequent files to reduce glitches
                        if i > 0:
                            infile.read(1024)  # Skip first 1024 bytes
                        outfile.write(infile.read())
            
            logger.info(f"✓ Successfully combined {len(chunk_files)} ElevenLabs chunks: {final_file}")
            return final_file
            
        except Exception as e:
            logger.error(f"Error in ElevenLabs chunk combination: {e}")
            # Return the first chunk as last resort
            logger.warning(f"Falling back to first chunk: {chunk_files[0]}")
            return chunk_files[0]
    
    def _cleanup_chunk_files(self, chunk_files: List[str]):
        """Clean up temporary chunk files after combining."""
        for chunk_file in chunk_files:
            try:
                Path(chunk_file).unlink()
                logger.debug(f"Deleted temporary ElevenLabs chunk: {Path(chunk_file).name}")
            except Exception as e:
                logger.warning(f"Could not delete ElevenLabs chunk file {chunk_file}: {e}")
        
        logger.info(f"Cleaned up {len(chunk_files)} temporary ElevenLabs chunk files")
    
    def get_supported_voices(self) -> List[str]:
        """Get list of available voices from ElevenLabs API."""
        url = "https://api.elevenlabs.io/v1/voices"
        headers = {"xi-api-key": self.api_key}
        
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                voices_data = response.json()
                voices = [(voice['voice_id'], voice['name']) for voice in voices_data.get('voices', [])]
                return voices
            else:
                logger.error(f"Failed to fetch ElevenLabs voices: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Error fetching ElevenLabs voices: {str(e)}")
            return []
    
    def get_supported_models(self) -> List[str]:
        """Get list of supported ElevenLabs models."""
        return [
            "eleven_multilingual_v2",
            "eleven_turbo_v2_5",
            "eleven_monolingual_v1",
            "eleven_multilingual_v1"
        ]