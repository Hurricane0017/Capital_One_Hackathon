#!/usr/bin/env python3

import os
import json
import time
import logging
import shutil
from datetime import datetime
from pathlib import Path
import threading
from typing import Dict, List, Optional, Tuple
import signal
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Audio processing
import subprocess

# Google Cloud APIs for speech-to-text, translation and TTS
from google.cloud import speech
from google.cloud import translate_v2 as translate
from google.cloud import texttospeech

# Free translation alternatives
try:
    from deep_translator import GoogleTranslator, MyMemoryTranslator, LibreTranslator, PonsTranslator
    DEEP_TRANSLATOR_AVAILABLE = True
except ImportError:
    DEEP_TRANSLATOR_AVAILABLE = False

# Language detection and translation
from langdetect import detect, DetectorFactory

# File monitoring
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import traceback

# Set seed for consistent language detection
DetectorFactory.seed = 0

class RecordingProcessorGoogle:
    """Main class for processing call recordings with Google Cloud APIs"""
    
    def __init__(self, config_path: str = None):
        self.setup_logging()
        self.setup_directories()
        self.load_configuration(config_path)
        self.setup_models()
        self.processed_files = self.load_processed_files()
        self.running = False
        
    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('/Users/apple/Desktop/asterisk/recordings/processor.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def setup_directories(self):
        """Setup required directories"""
        self.base_dir = Path('/Users/apple/Desktop/asterisk')
        self.recordings_dir = self.base_dir / 'recordings'
        self.monitor_dir = self.base_dir / 'monitor'
        self.raw_dir = self.recordings_dir / 'raw'
        self.converted_dir = self.recordings_dir / 'converted'
        self.transcripts_dir = self.recordings_dir / 'transcripts'
        
        # Create directories if they don't exist
        for dir_path in [self.raw_dir, self.converted_dir, self.transcripts_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
            
    def load_configuration(self, config_path: str = None):
        """Load configuration settings"""
        default_config = {
            "translation_enabled": True,
            "target_language": "en",
            "audio_formats": [".ulaw", ".wav", ".gsm", ".mp3"],
            "monitoring_directories": [
                str(self.monitor_dir),
                str(self.recordings_dir / 'raw')
            ],
            "processing_delay": 2  # seconds to wait before processing new files
        }
        
        if config_path and os.path.exists(config_path):
            with open(config_path, 'r') as f:
                user_config = json.load(f)
                default_config.update(user_config)
                
        self.config = default_config
        self.logger.info(f"Configuration loaded: {self.config}")
        
    def setup_models(self):
        """Initialize Google Cloud Speech-to-Text, Translation, and TTS models"""
        # Initialize default values first to ensure attributes exist
        self.speech_client = None
        self.translate_client = None
        self.tts_client = None
        self.speech_config = None
        self.speech_model = 'latest_long'
        self.auto_detect = True
        self.voice_quality = 'neural2'
        self.sample_rate = 16000
        self.primary_language = 'hi-IN'
        self.translation_preference = ['free_google', 'mymemory', 'libretranslate', 'google_cloud', 'pons']
        
        # Create a basic speech config first to ensure it always exists
        try:
            self.speech_config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,  # Changed to WAV format
                sample_rate_hertz=self.sample_rate,
                language_code=self.primary_language,
                alternative_language_codes=['en-US', 'en-IN'] if self.auto_detect else [],
                enable_automatic_punctuation=True,
                diarization_config=speech.SpeakerDiarizationConfig(
                    enable_speaker_diarization=True,
                    min_speaker_count=1,
                    max_speaker_count=2
                ),
                model=self.speech_model,
                use_enhanced=True,
                profanity_filter=False,
                speech_contexts=[
                    speech.SpeechContext(
                        phrases=[
                            "नमस्ते", "धन्यवाद", "कैसे हैं", "अच्छा", "ठीक है"
                        ]
                    )
                ]
            )
            self.logger.info("Basic speech config created successfully")
        except Exception as e:
            self.logger.error(f"Failed to create basic speech config: {e}")
            # Create minimal fallback config
            self.speech_config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=16000,
                language_code='hi-IN'
            )
        
        try:
            self.logger.info("Setting up Google Cloud Speech-to-Text, Translation, and TTS APIs")
            
            # Load credentials from .env file
            google_api_key = os.getenv('GOOGLE_CLOUD_API_KEY')
            credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
            project_id = os.getenv('GOOGLE_CLOUD_PROJECT_ID')
            
            # Load configuration from .env
            self.speech_model = os.getenv('SPEECH_TO_TEXT_MODEL', 'latest_long')
            self.auto_detect = os.getenv('LANGUAGE_AUTO_DETECT', 'true').lower() == 'true'
            self.voice_quality = os.getenv('TTS_VOICE_QUALITY', 'neural2')
            self.sample_rate = int(os.getenv('AUDIO_SAMPLE_RATE', '16000'))
            self.primary_language = os.getenv('PRIMARY_LANGUAGE', 'hi-IN')  # Default to Hindi
            
            # Translation service preference (comma-separated) - Prioritize Google Cloud Translation API
            self.translation_preference = os.getenv('TRANSLATION_SERVICES', 'google_cloud,free_google,mymemory,libretranslate,pons').split(',')
            
            self.logger.info(f"Using Google Cloud Speech model: {self.speech_model}")
            self.logger.info(f"Primary language: {self.primary_language}")
            self.logger.info(f"Auto language detection: {self.auto_detect}")
            self.logger.info(f"TTS voice quality: {self.voice_quality}")
            self.logger.info(f"Translation services preference: {self.translation_preference}")
            
            # Check for deep-translator availability
            if DEEP_TRANSLATOR_AVAILABLE:
                self.logger.info("✅ deep-translator library available - free translation services enabled")
            else:
                self.logger.warning("⚠️ deep-translator library not found - only Google Cloud translation available")
                self.logger.info("Install with: pip install deep-translator")
            
            # Update speech config with environment variables
            try:
                self.speech_config = speech.RecognitionConfig(
                    encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,  # WAV format
                    sample_rate_hertz=self.sample_rate,
                    language_code=self.primary_language,
                    alternative_language_codes=['en-US', 'en-IN'] if self.auto_detect else [],
                    enable_automatic_punctuation=True,
                    diarization_config=speech.SpeakerDiarizationConfig(
                        enable_speaker_diarization=True,
                        min_speaker_count=1,
                        max_speaker_count=2
                    ),
                    model=self.speech_model,
                    use_enhanced=True,  # Use enhanced model for better accuracy
                    profanity_filter=False,
                    speech_contexts=[
                        speech.SpeechContext(
                            phrases=[
                                # Add common Hindi phrases for better recognition
                                "नमस्ते", "धन्यवाद", "कैसे हैं", "अच्छा", "ठीक है"
                            ]
                        )
                    ]
                )
                self.logger.info("Updated speech config with environment variables")
            except Exception as e:
                self.logger.warning(f"Failed to update speech config with environment variables: {e}")
                self.logger.info("Using basic speech config")
            
            # Setup Google Cloud Authentication
            if google_api_key:
                self.logger.info("Using Google Cloud API key authentication")
                os.environ['GOOGLE_API_KEY'] = google_api_key
                if project_id:
                    os.environ['GOOGLE_CLOUD_PROJECT'] = project_id
                    
            elif credentials_path:
                self.logger.info(f"Using Google Cloud service account from: {credentials_path}")
                if not os.path.exists(credentials_path):
                    raise FileNotFoundError(f"Service account file not found: {credentials_path}")
                    
            else:
                self.logger.warning("No Google Cloud credentials found. Speech recognition, translation and TTS may not work.")
            
            # Initialize Google Cloud clients
            try:
                self.speech_client = speech.SpeechClient()
                self.translate_client = translate.Client()
                self.tts_client = texttospeech.TextToSpeechClient()
                self.logger.info("Google Cloud Speech-to-Text, Translation and TTS initialized successfully")
            except Exception as e:
                self.logger.error(f"Google Cloud services initialization failed: {e}")
                self.speech_client = None
                self.translate_client = None
                self.tts_client = None
                # Don't return False here - speech_config is still available for structure
            
            self.logger.info("Google Cloud Speech recognition configured successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Google Cloud APIs: {e}")
            import traceback
            traceback.print_exc()
            
            # Ensure speech_config is still available even on failure
            if not hasattr(self, 'speech_config') or self.speech_config is None:
                self.speech_config = speech.RecognitionConfig(
                    encoding=speech.RecognitionConfig.AudioEncoding.FLAC,
                    sample_rate_hertz=self.sample_rate,
                    language_code=self.primary_language,
                    enable_automatic_punctuation=True,
                    model='latest_long'
                )
            
            return False
    
    def is_file_ready(self, filepath: Path, stability_time: int = 5, max_wait: int = 120) -> bool:
        """
        Check if file is ready for processing by ensuring it's stable (not being written to)
        
        Args:
            filepath: Path to the file to check
            stability_time: Seconds the file size must remain stable
            max_wait: Maximum time to wait for file stability
            
        Returns:
            bool: True if file is ready, False if still being written or timeout
        """
        try:
            if not filepath.exists():
                return False
            
            self.logger.info(f"Checking file readiness: {filepath.name}")
            
            # Check for completion marker file first (more reliable for Asterisk recordings)
            completion_marker = filepath.with_suffix('.complete')
            if completion_marker.exists():
                self.logger.info(f"Found completion marker for {filepath.name}")
                return True
            
            # Fall back to file size stability check
            # Initial file size
            initial_size = filepath.stat().st_size
            last_size = initial_size
            stable_count = 0
            total_wait = 0
            
            # If file is very small (< 1KB), it might still be being created
            if initial_size < 1024:
                self.logger.info(f"File {filepath.name} is very small ({initial_size} bytes), waiting...")
                time.sleep(2)
            
            while total_wait < max_wait:
                time.sleep(1)  # Check every second
                total_wait += 1
                
                # Check again for completion marker
                if completion_marker.exists():
                    self.logger.info(f"Completion marker appeared for {filepath.name} after {total_wait}s")
                    return True
                
                try:
                    current_size = filepath.stat().st_size
                    
                    if current_size == last_size:
                        stable_count += 1
                        if stable_count >= stability_time:
                            self.logger.info(f"File {filepath.name} is stable ({current_size} bytes) after {total_wait}s")
                            return True
                    else:
                        # File size changed, reset stability counter
                        stable_count = 0
                        self.logger.info(f"File {filepath.name} size changed: {last_size} -> {current_size} bytes")
                        last_size = current_size
                    
                except (OSError, FileNotFoundError):
                    # File might have been moved or deleted
                    self.logger.warning(f"File {filepath.name} became inaccessible")
                    return False
            
            self.logger.warning(f"File {filepath.name} did not stabilize within {max_wait}s (final size: {last_size} bytes)")
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking file readiness for {filepath}: {e}")
            return False
            
    def load_processed_files(self) -> List[str]:
        """Load list of already processed files"""
        processed_file_path = self.recordings_dir / 'processed_files.json'
        if processed_file_path.exists():
            try:
                with open(processed_file_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"Error loading processed files: {e}")
        return []
        
    def save_processed_files(self):
        """Save list of processed files"""
        processed_file_path = self.recordings_dir / 'processed_files.json'
        try:
            with open(processed_file_path, 'w') as f:
                json.dump(self.processed_files, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving processed files: {e}")
            
    def convert_audio_to_wav(self, input_path: Path) -> Path:
        """Convert audio file to WAV format for Google Cloud Speech recognition"""
        try:
            # Output path
            output_path = self.converted_dir / f"{input_path.stem}.wav"
            
            # Determine ffmpeg input format based on file extension
            file_ext = input_path.suffix.lower()
            
            if file_ext == '.ulaw':
                cmd = [
                    'ffmpeg', '-y',
                    '-f', 'mulaw', '-ar', '8000', '-ac', '1',
                    '-i', str(input_path),
                    '-ar', str(self.sample_rate),
                    '-ac', '1',
                    '-acodec', 'pcm_s16le',
                    str(output_path)
                ]
            elif file_ext == '.gsm':
                cmd = [
                    'ffmpeg', '-y',
                    '-f', 'gsm', '-ar', '8000',
                    '-i', str(input_path),
                    '-ar', str(self.sample_rate),
                    '-ac', '1',
                    '-acodec', 'pcm_s16le',
                    str(output_path)
                ]
            elif file_ext in ['.wav']:
                # Already WAV, just ensure proper settings
                cmd = [
                    'ffmpeg', '-y',
                    '-i', str(input_path),
                    '-ar', str(self.sample_rate),
                    '-ac', '1',
                    '-acodec', 'pcm_s16le',
                    str(output_path)
                ]
            else:
                # For other formats (mp3, flac, etc.)
                cmd = [
                    'ffmpeg', '-y',
                    '-i', str(input_path),
                    '-ar', str(self.sample_rate),
                    '-ac', '1',
                    '-acodec', 'pcm_s16le',
                    str(output_path)
                ]
            
            # Run ffmpeg conversion
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=300  # 5 minutes for longer recordings
            )
            
            if result.returncode == 0:
                self.logger.info(f"Converted {input_path.name} to WAV format")
                return output_path
            else:
                raise RuntimeError(f"ffmpeg failed: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            self.logger.error(f"Timeout converting {input_path.name}")
            raise
        except Exception as e:
            self.logger.error(f"Error converting {input_path.name} to WAV: {e}")
            raise
            
    def transcribe_audio(self, audio_path: Path) -> Dict:
        """Transcribe audio file to text using Google Cloud Speech-to-Text with Hindi support"""
        try:
            self.logger.info(f"Transcribing audio with Google Cloud Speech-to-Text: {audio_path.name}")
            
            if not self.speech_client:
                return {
                    "transcript": "",
                    "language": "unknown",
                    "confidence": 0.0,
                    "error": "Google Cloud Speech client not initialized"
                }
            
            # Check file size and duration
            file_size = audio_path.stat().st_size
            self.logger.info(f"Audio file size: {file_size / (1024*1024):.2f} MB")
            
            # Get audio duration using ffprobe
            duration = self._get_audio_duration(audio_path)
            self.logger.info(f"Audio duration: {duration:.2f} seconds")
            
            # Read audio file
            with open(audio_path, 'rb') as audio_file:
                audio_content = audio_file.read()
            
            # Create audio object
            audio = speech.RecognitionAudio(content=audio_content)
            
            # Choose recognition method based on duration
            if duration <= 60:
                # Use synchronous recognition for shorter audio
                self.logger.info("Using synchronous recognition (audio <= 60 seconds)")
                response = self.speech_client.recognize(
                    config=self.speech_config,
                    audio=audio
                )
                results = response.results
                
            else:
                # Use asynchronous long-running recognition for longer audio
                self.logger.info("Using asynchronous long-running recognition (audio > 60 seconds)")
                
                # For long audio, we need to upload to Google Cloud Storage or use streaming
                # For now, we'll try with the content method but may need to implement GCS upload
                try:
                    operation = self.speech_client.long_running_recognize(
                        config=self.speech_config,
                        audio=audio
                    )
                    
                    self.logger.info("Waiting for long-running recognition to complete...")
                    response = operation.result(timeout=600)  # 10 minute timeout
                    results = response.results
                    
                except Exception as e:
                    self.logger.warning(f"Long-running recognition failed, trying chunked approach: {e}")
                    # Fallback to chunked processing
                    return self._transcribe_audio_chunked(audio_path, duration)
            
            if not results:
                self.logger.warning("No transcription results returned")
                return {
                    "transcript": "",
                    "language": "unknown",
                    "confidence": 0.0,
                    "error": "No transcription results"
                }
            
            # Process results
            transcript_parts = []
            total_confidence = 0.0
            confidence_count = 0
            detected_language = self.primary_language
            speakers = []
            
            for i, result in enumerate(results):
                if result.alternatives:
                    best_alternative = result.alternatives[0]
                    transcript_parts.append(best_alternative.transcript)
                    
                    # Aggregate confidence
                    if best_alternative.confidence:
                        total_confidence += best_alternative.confidence
                        confidence_count += 1
                    
                    # Extract speaker information if available
                    if hasattr(result, 'speaker_tag') and result.speaker_tag:
                        speakers.append({
                            "speaker": f"Speaker {result.speaker_tag}",
                            "text": best_alternative.transcript,
                            "confidence": best_alternative.confidence or 0.8
                        })
                    
                    # Try to detect language from first result
                    if i == 0 and hasattr(best_alternative, 'language_code'):
                        detected_language = best_alternative.language_code
            
            # Combine transcript
            full_transcript = " ".join(transcript_parts).strip()
            average_confidence = total_confidence / confidence_count if confidence_count > 0 else 0.8
            
            self.logger.info(f"Transcription completed. Length: {len(full_transcript)} chars, Language: {detected_language}, Confidence: {average_confidence:.3f}")
            
            # Normalize language code
            normalized_language = self._normalize_language_code(detected_language)
            
            result_dict = {
                "transcript": full_transcript,
                "language": normalized_language,
                "confidence": average_confidence,
                "duration": duration,
                "file_size_mb": file_size / (1024*1024)
            }
            
            # Add speaker information if available
            if speakers:
                result_dict["speakers"] = speakers
                self.logger.info(f"Detected {len(speakers)} speaker segments")
            
            return result_dict
            
        except Exception as e:
            self.logger.error(f"Error transcribing {audio_path.name}: {e}")
            import traceback
            traceback.print_exc()
            return {
                "transcript": "",
                "language": "unknown", 
                "confidence": 0.0,
                "error": str(e)
            }
    
    def _get_audio_duration(self, audio_path: Path) -> float:
        """Get audio duration in seconds using ffprobe"""
        try:
            cmd = [
                'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
                '-of', 'csv=p=0', str(audio_path)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                duration = float(result.stdout.strip())
                return duration
            else:
                self.logger.warning(f"Could not get duration for {audio_path.name}, assuming 60 seconds")
                return 60.0
                
        except Exception as e:
            self.logger.warning(f"Error getting audio duration: {e}, assuming 60 seconds")
            return 60.0
    
    def _transcribe_audio_chunked(self, audio_path: Path, duration: float) -> Dict:
        """Transcribe long audio by splitting into chunks"""
        try:
            self.logger.info(f"Transcribing audio in chunks: {audio_path.name}")
            
            # Split audio into 50-second chunks with 5-second overlap
            chunk_duration = 50
            overlap = 5
            chunks = []
            
            current_start = 0
            chunk_index = 0
            
            while current_start < duration:
                chunk_end = min(current_start + chunk_duration, duration)
                
                # Create chunk file
                chunk_path = self.converted_dir / f"{audio_path.stem}_chunk_{chunk_index:03d}.wav"
                
                cmd = [
                    'ffmpeg', '-y',
                    '-i', str(audio_path),
                    '-ss', str(current_start),
                    '-t', str(chunk_end - current_start),
                    '-acodec', 'pcm_s16le',
                    str(chunk_path)
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                
                if result.returncode == 0:
                    chunks.append(chunk_path)
                    self.logger.info(f"Created chunk {chunk_index}: {current_start:.1f}s - {chunk_end:.1f}s")
                else:
                    self.logger.error(f"Failed to create chunk {chunk_index}")
                
                chunk_index += 1
                current_start += chunk_duration - overlap
            
            # Transcribe each chunk
            all_transcripts = []
            total_confidence = 0.0
            confidence_count = 0
            
            for i, chunk_path in enumerate(chunks):
                try:
                    with open(chunk_path, 'rb') as audio_file:
                        audio_content = audio_file.read()
                    
                    audio = speech.RecognitionAudio(content=audio_content)
                    
                    response = self.speech_client.recognize(
                        config=self.speech_config,
                        audio=audio
                    )
                    
                    if response.results:
                        for result in response.results:
                            if result.alternatives:
                                best_alternative = result.alternatives[0]
                                all_transcripts.append(best_alternative.transcript)
                                
                                if best_alternative.confidence:
                                    total_confidence += best_alternative.confidence
                                    confidence_count += 1
                    
                    self.logger.info(f"Transcribed chunk {i+1}/{len(chunks)}")
                    
                    # Clean up chunk file
                    chunk_path.unlink()
                    
                except Exception as e:
                    self.logger.error(f"Error transcribing chunk {i}: {e}")
            
            # Combine results
            full_transcript = " ".join(all_transcripts).strip()
            average_confidence = total_confidence / confidence_count if confidence_count > 0 else 0.8
            
            normalized_language = self._normalize_language_code(self.primary_language)
            
            return {
                "transcript": full_transcript,
                "language": normalized_language,
                "confidence": average_confidence,
                "duration": duration,
                "chunks_processed": len(chunks)
            }
            
        except Exception as e:
            self.logger.error(f"Error in chunked transcription: {e}")
            return {
                "transcript": "",
                "language": "unknown",
                "confidence": 0.0,
                "error": str(e)
            }
            
    def _normalize_language_code(self, lang_code: str) -> str:
        """Normalize language codes from Google Cloud to standard format"""
        # Map Google Cloud language codes to standard codes
        google_language_mapping = {
            'en-us': 'en', 'en-gb': 'en', 'en-au': 'en', 'en-ca': 'en', 'en-in': 'en',
            'hi-in': 'hi', 'bn-in': 'bn', 'te-in': 'te', 'mr-in': 'mr',
            'ta-in': 'ta', 'gu-in': 'gu', 'ur-in': 'ur', 'kn-in': 'kn',
            'or-in': 'or', 'pa-in': 'pa', 'as-in': 'as', 'ml-in': 'ml',
            'es-es': 'es', 'es-mx': 'es', 'es-us': 'es',
            'fr-fr': 'fr', 'fr-ca': 'fr',
            'de-de': 'de', 'it-it': 'it', 'pt-br': 'pt', 'pt-pt': 'pt',
            'ru-ru': 'ru', 'ja-jp': 'ja', 'ko-kr': 'ko',
            'zh-cn': 'zh', 'zh-tw': 'zh', 'ar-xa': 'ar',
            'nl-nl': 'nl', 'sv-se': 'sv'
        }
        
        normalized = google_language_mapping.get(lang_code.lower(), lang_code.lower())
        # Extract base language code if it contains region info
        if '-' in normalized:
            normalized = normalized.split('-')[0]
        return normalized
            
    def translate_text(self, text: str, source_lang: str, target_lang: str = "en") -> Dict:
        """Translate text to target language using multiple translation services"""
        try:
            if source_lang == target_lang or not text.strip():
                return {
                    "translated_text": text,
                    "source_language": source_lang,
                    "target_language": target_lang,
                    "success": True,
                    "service": "no_translation_needed"
                }
            
            # Split long text into chunks to avoid API limits - Google Cloud can handle larger chunks
            max_chunk_size = 10000 if 'google_cloud' in self.translation_preference[:2] else 4000  # Google Cloud has higher limits
            text_chunks = self._split_text_into_chunks(text, max_chunk_size)
            translated_chunks = []
            
            self.logger.info(f"Translating {len(text_chunks)} chunks from {source_lang} to {target_lang} (chunk size: {max_chunk_size})")
            
            # Try translation services in order of preference - Google Cloud first for reliability
            translation_services = []
            
            # Build services list based on preference and availability
            for service_name in self.translation_preference:
                if service_name == 'google_cloud' and self.translate_client:
                    translation_services.append(self._translate_with_google_cloud)
                elif service_name == 'free_google' and DEEP_TRANSLATOR_AVAILABLE:
                    translation_services.append(self._translate_with_free_google)
                elif service_name == 'mymemory' and DEEP_TRANSLATOR_AVAILABLE:
                    translation_services.append(self._translate_with_mymemory)
                elif service_name == 'libretranslate' and DEEP_TRANSLATOR_AVAILABLE:
                    translation_services.append(self._translate_with_libre)
                elif service_name == 'pons' and DEEP_TRANSLATOR_AVAILABLE:
                    translation_services.append(self._translate_with_pons)
            
            # Fallback services if none were added from preferences
            if not translation_services:
                if self.translate_client:
                    translation_services.append(self._translate_with_google_cloud)
                if DEEP_TRANSLATOR_AVAILABLE:
                    translation_services.extend([
                        self._translate_with_free_google,
                        self._translate_with_mymemory,
                        self._translate_with_libre,
                        self._translate_with_pons
                    ])
            
            successful_service = None
            
            for service_func in translation_services:
                try:
                    all_success = True
                    translated_chunks = []
                    
                    for chunk in text_chunks:
                        if not chunk.strip():
                            translated_chunks.append(chunk)
                            continue
                            
                        result = service_func(chunk, source_lang, target_lang)
                        if result["success"]:
                            translated_chunks.append(result["translated_text"])
                        else:
                            all_success = False
                            break
                    
                    if all_success:
                        successful_service = result.get("service", service_func.__name__)
                        break
                        
                except Exception as e:
                    self.logger.warning(f"Translation service {service_func.__name__} failed: {e}")
                    continue
            
            if translated_chunks and successful_service:
                final_translation = " ".join(translated_chunks)
                self.logger.info(f"Translation successful using {successful_service}")
                
                return {
                    "translated_text": final_translation,
                    "source_language": source_lang,
                    "target_language": target_lang,
                    "success": True,
                    "service": successful_service,
                    "chunks_processed": len(text_chunks)
                }
            
            # All services failed, use offline fallback
            self.logger.warning("All translation services failed, using offline fallback")
            return self._get_offline_translation(text, source_lang, target_lang)
            
        except Exception as e:
            self.logger.error(f"Translation failed: {e}")
            return self._get_offline_translation(text, source_lang, target_lang)
    
    def _split_text_into_chunks(self, text: str, max_size: int) -> List[str]:
        """Split text into chunks that respect sentence boundaries and preserve context"""
        if len(text) <= max_size:
            return [text]
        
        chunks = []
        
        # Try to split by sentences first (works for most languages)
        # Handle multiple sentence endings for better language support
        sentence_endings = ['. ', '! ', '? ', '। ', '॥ ', '|']  # Include Hindi sentence endings
        
        # Find sentence boundaries
        sentences = []
        current_sentence = ""
        i = 0
        
        while i < len(text):
            current_sentence += text[i]
            
            # Check for sentence endings
            for ending in sentence_endings:
                if text[i:i+len(ending)] == ending:
                    sentences.append(current_sentence)
                    current_sentence = ""
                    i += len(ending) - 1
                    break
            i += 1
        
        # Add remaining text as last sentence
        if current_sentence.strip():
            sentences.append(current_sentence)
        
        # If no clear sentences found, split by line breaks or word boundaries
        if len(sentences) <= 1:
            if '\n' in text:
                sentences = text.split('\n')
            else:
                # Split by words as last resort
                words = text.split(' ')
                sentences = []
                current = ""
                for word in words:
                    if len(current + word + " ") <= max_size // 2:  # Conservative chunking
                        current += word + " "
                    else:
                        if current:
                            sentences.append(current.strip())
                        current = word + " "
                if current:
                    sentences.append(current.strip())
        
        # Combine sentences into chunks
        current_chunk = ""
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            # Check if adding this sentence would exceed the limit
            if len(current_chunk + sentence + " ") <= max_size:
                current_chunk += sentence + " "
            else:
                # Save current chunk and start new one
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    
                # Handle very long sentences that exceed max_size
                if len(sentence) > max_size:
                    # Split long sentence by words
                    words = sentence.split()
                    temp_chunk = ""
                    for word in words:
                        if len(temp_chunk + word + " ") <= max_size:
                            temp_chunk += word + " "
                        else:
                            if temp_chunk:
                                chunks.append(temp_chunk.strip())
                            temp_chunk = word + " "
                    current_chunk = temp_chunk
                else:
                    current_chunk = sentence + " "
        
        # Add the last chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        # Fallback: if still no chunks, force split
        if not chunks:
            for i in range(0, len(text), max_size):
                chunks.append(text[i:i + max_size])
        
        self.logger.info(f"Split text into {len(chunks)} chunks for translation")
        return chunks
    
    def _translate_with_free_google(self, text: str, source_lang: str, target_lang: str) -> Dict:
        """Translate using free Google Translator (deep-translator)"""
        if not DEEP_TRANSLATOR_AVAILABLE:
            return {"success": False, "error": "deep-translator not available"}
        
        try:
            # Use auto-detect if source language is unknown
            if source_lang == "unknown" or not source_lang:
                translator = GoogleTranslator(source='auto', target=target_lang)
            else:
                translator = GoogleTranslator(source=source_lang, target=target_lang)
            
            translated = translator.translate(text)
            
            return {
                "translated_text": translated,
                "source_language": source_lang,
                "target_language": target_lang,
                "success": True,
                "service": "free_google"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e), "service": "free_google"}
    
    def _translate_with_mymemory(self, text: str, source_lang: str, target_lang: str) -> Dict:
        """Translate using MyMemory API (free with generous limits)"""
        if not DEEP_TRANSLATOR_AVAILABLE:
            return {"success": False, "error": "deep-translator not available"}
        
        try:
            # MyMemory supports auto-detection
            if source_lang == "unknown" or not source_lang:
                translator = MyMemoryTranslator(source='auto', target=target_lang)
            else:
                translator = MyMemoryTranslator(source=source_lang, target=target_lang)
            
            translated = translator.translate(text)
            
            return {
                "translated_text": translated,
                "source_language": source_lang,
                "target_language": target_lang,
                "success": True,
                "service": "mymemory"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e), "service": "mymemory"}
    
    def _translate_with_libre(self, text: str, source_lang: str, target_lang: str) -> Dict:
        """Translate using LibreTranslate (free and open source)"""
        if not DEEP_TRANSLATOR_AVAILABLE:
            return {"success": False, "error": "deep-translator not available"}
        
        try:
            # LibreTranslate requires specific language codes
            libre_lang_map = {
                'hi': 'hi', 'bn': 'bn', 'es': 'es', 'fr': 'fr', 'de': 'de',
                'it': 'it', 'pt': 'pt', 'ru': 'ru', 'ja': 'ja', 'ko': 'ko',
                'zh': 'zh', 'ar': 'ar', 'nl': 'nl', 'sv': 'sv', 'en': 'en'
            }
            
            source_code = libre_lang_map.get(source_lang, 'auto')
            target_code = libre_lang_map.get(target_lang, 'en')
            
            if source_code == 'auto' or source_lang == "unknown":
                # LibreTranslate auto-detection
                translator = LibreTranslator(source='auto', target=target_code, base_url='https://libretranslate.de')
            else:
                translator = LibreTranslator(source=source_code, target=target_code, base_url='https://libretranslate.de')
            
            translated = translator.translate(text)
            
            return {
                "translated_text": translated,
                "source_language": source_lang,
                "target_language": target_lang,
                "success": True,
                "service": "libretranslate"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e), "service": "libretranslate"}
    
    def _translate_with_google_cloud(self, text: str, source_lang: str, target_lang: str) -> Dict:
        """Translate using Google Cloud Translation API (paid but most accurate and reliable)"""
        if not self.translate_client:
            return {"success": False, "error": "Google Cloud Translation not configured"}
        
        try:
            # Clean and prepare text for translation
            text = text.strip()
            if not text:
                return {"success": False, "error": "Empty text provided"}
            
            self.logger.info(f"Using Google Cloud Translation API for {len(text)} characters")
            
            # Auto-detect source language if not specified or unknown
            if source_lang == "unknown" or not source_lang or source_lang == "auto":
                self.logger.info("Auto-detecting source language with Google Cloud")
                result = self.translate_client.translate(
                    text,
                    target_language=target_lang,
                    format_='text'  # Ensure plain text format
                )
                
                detected_source = result.get('detectedSourceLanguage', 'unknown')
                translated_text = result['translatedText']
                
                self.logger.info(f"Google Cloud detected source language: {detected_source}")
                
                return {
                    "translated_text": translated_text,
                    "source_language": detected_source,
                    "target_language": target_lang,
                    "success": True,
                    "service": "google_cloud",
                    "auto_detected": True
                }
            else:
                # Use specified source language
                self.logger.info(f"Translating from {source_lang} to {target_lang} using Google Cloud")
                result = self.translate_client.translate(
                    text,
                    source_language=source_lang,
                    target_language=target_lang,
                    format_='text'  # Ensure plain text format
                )
                
                translated_text = result['translatedText']
                
                return {
                    "translated_text": translated_text,
                    "source_language": source_lang,
                    "target_language": target_lang,
                    "success": True,
                    "service": "google_cloud",
                    "auto_detected": False
                }
            
        except Exception as e:
            self.logger.error(f"Google Cloud Translation failed: {e}")
            return {"success": False, "error": str(e), "service": "google_cloud"}
    
    def _translate_with_pons(self, text: str, source_lang: str, target_lang: str) -> Dict:
        """Translate using PONS dictionary (good for short phrases)"""
        if not DEEP_TRANSLATOR_AVAILABLE:
            return {"success": False, "error": "deep-translator not available"}
        
        try:
            # PONS works well for shorter texts
            if len(text) > 500:
                return {"success": False, "error": "Text too long for PONS", "service": "pons"}
            
            # PONS language mapping
            pons_lang_map = {
                'es': 'spanish', 'fr': 'french', 'de': 'german', 'it': 'italian',
                'pt': 'portuguese', 'ru': 'russian', 'en': 'english'
            }
            
            source_name = pons_lang_map.get(source_lang)
            target_name = pons_lang_map.get(target_lang)
            
            if not source_name or not target_name:
                return {"success": False, "error": "Language not supported by PONS", "service": "pons"}
            
            translator = PonsTranslator(source=source_name, target=target_name)
            translated = translator.translate(text)
            
            return {
                "translated_text": translated,
                "source_language": source_lang,
                "target_language": target_lang,
                "success": True,
                "service": "pons"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e), "service": "pons"}
    
    def _get_offline_translation(self, text: str, source_lang: str, target_lang: str) -> Dict:
        """Fallback offline translation for common phrases"""
        try:
            # Check for simple translations
            text_lower = text.lower().strip()
            
            # Simple phrase translations for common cases (extensive Indian languages)
            simple_translations = {
                "hi": {
                    "hello": "नमस्ते",
                    "hello world": "नमस्ते दुनिया", 
                    "how are you": "आप कैसे हैं",
                    "thank you": "धन्यवाद",
                    "goodbye": "अलविदा",
                    "yes": "हाँ",
                    "no": "नहीं"
                },
                "bn": {
                    "hello": "নমস্কার",
                    "hello world": "নমস্কার পৃথিবী",
                    "how are you": "আপনি কেমন আছেন",
                    "thank you": "ধন্যবাদ",
                    "goodbye": "বিদায়"
                },
                "en": {
                    "hello": "hello",
                    "hello world": "hello world",
                    "how are you": "how are you",
                    "thank you": "thank you",
                    "goodbye": "goodbye"
                }
            }
            
            # If translating TO a supported language
            if target_lang in simple_translations and source_lang == "en":
                translated = simple_translations[target_lang].get(text_lower, text)
                return {
                    "translated_text": translated,
                    "source_language": source_lang,
                    "target_language": target_lang,
                    "success": translated != text,
                    "fallback": True
                }
            
            # If translating FROM a supported language to English
            if source_lang in simple_translations and target_lang == "en":
                reverse_dict = {v: k for k, v in simple_translations[source_lang].items()}
                translated = reverse_dict.get(text_lower, text)
                return {
                    "translated_text": translated,
                    "source_language": source_lang,
                    "target_language": target_lang,
                    "success": translated != text,
                    "fallback": True
                }
            
            # If no offline translation available, return original text
            self.logger.warning(f"No offline translation available for '{text}' from {source_lang} to {target_lang}")
            return {
                "translated_text": text,
                "source_language": source_lang,
                "target_language": target_lang,
                "success": False,
                "error": "Translation service unavailable, used original text"
            }
                
        except Exception as e:
            self.logger.error(f"Offline translation failed: {e}")
            return {
                "translated_text": text,
                "source_language": source_lang,
                "target_language": target_lang,
                "success": False,
                "error": str(e)
            }
            
    def get_supported_languages(self) -> List[Dict]:
        """Get list of supported languages from Google Translate"""
        try:
            self.logger.info("Getting supported languages from Google Translate")
            
            # Get supported languages from Google Translate
            results = self.translate_client.get_languages()
            
            # Convert to our format
            supported_languages = []
            for language in results:
                supported_languages.append({
                    "code": language['language'],
                    "name": language['name']
                })
            
            self.logger.info(f"Retrieved {len(supported_languages)} supported languages from Google Translate")
            return supported_languages
            
        except Exception as e:
            self.logger.error(f"Error fetching supported languages from Google Translate: {e}")
            # Fallback to comprehensive language list
            self.logger.info("Using fallback comprehensive language list")
            return [
                # Major World Languages
                {"code": "en", "name": "English"},
                {"code": "es", "name": "Spanish"},
                {"code": "fr", "name": "French"},
                {"code": "de", "name": "German"},
                {"code": "it", "name": "Italian"},
                {"code": "pt", "name": "Portuguese"},
                {"code": "ru", "name": "Russian"},
                {"code": "ja", "name": "Japanese"},
                {"code": "ko", "name": "Korean"},
                {"code": "zh", "name": "Chinese"},
                {"code": "ar", "name": "Arabic"},
                {"code": "nl", "name": "Dutch"},
                {"code": "sv", "name": "Swedish"},
                
                # Major Indian Languages
                {"code": "hi", "name": "Hindi"},
                {"code": "bn", "name": "Bengali"},
                {"code": "te", "name": "Telugu"},
                {"code": "mr", "name": "Marathi"},
                {"code": "ta", "name": "Tamil"},
                {"code": "gu", "name": "Gujarati"},
                {"code": "ur", "name": "Urdu"},
                {"code": "kn", "name": "Kannada"},
                {"code": "or", "name": "Odia"},
                {"code": "pa", "name": "Punjabi"},
                {"code": "as", "name": "Assamese"},
                {"code": "ml", "name": "Malayalam"},
                {"code": "sa", "name": "Sanskrit"},
                {"code": "ne", "name": "Nepali"},
                
                # South Asian Languages
                {"code": "si", "name": "Sinhala"},
                {"code": "my", "name": "Burmese"}
            ]
            
    def translate_to_language(self, english_text: str, target_language: str) -> Dict:
        """Translate English text to specified target language"""
        try:
            self.logger.info(f"Translating English text to {target_language}")
            
            # If target is English, no translation needed
            if target_language.lower() == "en":
                return {
                    "original_text": english_text,
                    "translated_text": english_text,
                    "source_language": "en",
                    "target_language": "en",
                    "success": True
                }
            
            # Try online translation first
            translation_result = self.translate_text(english_text, "en", target_language)
            
            if translation_result["success"]:
                return {
                    "original_text": english_text,
                    "translated_text": translation_result["translated_text"],
                    "source_language": "en",
                    "target_language": target_language,
                    "success": True
                }
            
            # Fallback to simple phrase translations for common cases (extensive Indian languages)
            return {
                "original_text": english_text,
                "translated_text": english_text,  # Keep original if translation fails
                "source_language": "en",
                "target_language": target_language,
                "success": False,
                "error": translation_result.get("error", "Translation failed")
            }
                
        except Exception as e:
            self.logger.error(f"Error translating to {target_language}: {e}")
            return {
                "original_text": english_text,
                "translated_text": english_text,
                "source_language": "en",
                "target_language": target_language,
                "success": False,
                "error": str(e)
            }
            
    def _chunk_text_for_tts(self, text: str, max_bytes: int = 4500) -> List[str]:
        """
        Split text into chunks that don't exceed Google Cloud TTS byte limit.
        Uses 4500 bytes as a safe limit (below the 5000-byte limit).
        """
        if len(text.encode('utf-8')) <= max_bytes:
            return [text]
        
        chunks = []
        sentences = text.split('. ')
        current_chunk = ""
        
        for sentence in sentences:
            # Add period back if it's not the last sentence
            test_sentence = sentence + ('. ' if sentence != sentences[-1] else '')
            test_chunk = current_chunk + test_sentence
            
            # Check if adding this sentence would exceed the limit
            if len(test_chunk.encode('utf-8')) > max_bytes:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = test_sentence
                else:
                    # Single sentence is too long, split by words
                    words = sentence.split(' ')
                    word_chunk = ""
                    for word in words:
                        test_word_chunk = word_chunk + ' ' + word if word_chunk else word
                        if len(test_word_chunk.encode('utf-8')) > max_bytes:
                            if word_chunk:
                                chunks.append(word_chunk.strip())
                                word_chunk = word
                            else:
                                # Single word is too long, split by characters
                                char_chunk = ""
                                for char in word:
                                    test_char_chunk = char_chunk + char
                                    if len(test_char_chunk.encode('utf-8')) > max_bytes:
                                        if char_chunk:
                                            chunks.append(char_chunk)
                                        char_chunk = char
                                    else:
                                        char_chunk = test_char_chunk
                                if char_chunk:
                                    chunks.append(char_chunk)
                                word_chunk = ""
                        else:
                            word_chunk = test_word_chunk
                    if word_chunk:
                        current_chunk = word_chunk + ('. ' if sentence != sentences[-1] else '')
                    else:
                        current_chunk = ""
            else:
                current_chunk = test_chunk
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks

    def text_to_speech(self, text: str, language: str, voice_name: str = None) -> Path:
        """Convert text to speech audio file using Google Cloud Text-to-Speech"""
        try:
            self.logger.info(f"Converting text to speech in {language} using Google Cloud TTS")
            
            # Create generated_audio directory if it doesn't exist
            generated_audio_dir = self.recordings_dir / 'generated_audio'
            generated_audio_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            audio_filename = f"tts_{language}_{timestamp}"
            output_path = generated_audio_dir / f"{audio_filename}.mp3"
            metadata_path = generated_audio_dir / f"{audio_filename}_metadata.json"
            
            # Map language codes to Google Cloud TTS language codes and voices
            voice_mapping = self._get_google_tts_voice(language, voice_name)
            
            # Build the voice request
            voice = texttospeech.VoiceSelectionParams(
                language_code=voice_mapping['language_code'],
                name=voice_mapping['voice_name'],
                ssml_gender=voice_mapping['gender']
            )
            
            # Select the type of audio file you want returned
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=1.0,
                pitch=0.0,
                volume_gain_db=0.0
            )
            
            # Check if text exceeds Google Cloud TTS limits and chunk if necessary
            text_chunks = self._chunk_text_for_tts(text)
            
            if len(text_chunks) == 1:
                # Single chunk - process normally
                synthesis_input = texttospeech.SynthesisInput(text=text)
                response = self.tts_client.synthesize_speech(
                    input=synthesis_input, voice=voice, audio_config=audio_config
                )
                
                # Write the response to the output file
                with open(output_path, 'wb') as out:
                    out.write(response.audio_content)
            else:
                # Multiple chunks - process each and concatenate
                self.logger.info(f"Text too long, splitting into {len(text_chunks)} chunks")
                audio_segments = []
                
                for i, chunk in enumerate(text_chunks):
                    self.logger.info(f"Processing chunk {i+1}/{len(text_chunks)}")
                    synthesis_input = texttospeech.SynthesisInput(text=chunk)
                    response = self.tts_client.synthesize_speech(
                        input=synthesis_input, voice=voice, audio_config=audio_config
                    )
                    audio_segments.append(response.audio_content)
                
                # Concatenate audio segments using ffmpeg
                self._concatenate_audio_segments(audio_segments, output_path)
            
            # Create metadata file
            metadata = {
                "filename": output_path.name,
                "timestamp": datetime.now().isoformat(),
                "text": text,
                "language": language,
                "voice_name": voice_mapping['voice_name'],
                "language_code": voice_mapping['language_code'],
                "gender": voice_mapping['gender'],
                "format": "mp3",
                "service": "Google Cloud Text-to-Speech",
                "text_chunks": len(text_chunks),
                "original_text_bytes": len(text.encode('utf-8'))
            }
            
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"TTS audio generated successfully: {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(f"Error generating TTS audio: {e}")
            raise
    
    def _concatenate_audio_segments(self, audio_segments: List[bytes], output_path: Path):
        """Concatenate multiple audio segments into a single MP3 file"""
        import tempfile
        
        try:
            # Create temporary directory for audio segments
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_dir_path = Path(temp_dir)
                segment_files = []
                
                # Save each audio segment as a temporary file
                for i, audio_content in enumerate(audio_segments):
                    segment_file = temp_dir_path / f"segment_{i:03d}.mp3"
                    with open(segment_file, 'wb') as f:
                        f.write(audio_content)
                    segment_files.append(segment_file)
                
                # Create ffmpeg concat file
                concat_file = temp_dir_path / "concat.txt"
                with open(concat_file, 'w') as f:
                    for segment_file in segment_files:
                        f.write(f"file '{segment_file.absolute()}'\n")
                
                # Use ffmpeg to concatenate the segments
                ffmpeg_cmd = [
                    'ffmpeg', '-f', 'concat', '-safe', '0',
                    '-i', str(concat_file),
                    '-c', 'copy',
                    '-y',  # Overwrite output file
                    str(output_path)
                ]
                
                result = subprocess.run(
                    ffmpeg_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                if result.returncode != 0:
                    self.logger.error(f"ffmpeg concatenation failed: {result.stderr}")
                    # Fallback: just use the first segment
                    with open(output_path, 'wb') as f:
                        f.write(audio_segments[0])
                    self.logger.warning("Using first audio segment only due to concatenation failure")
                else:
                    self.logger.info(f"Successfully concatenated {len(audio_segments)} audio segments")
                    
        except Exception as e:
            self.logger.error(f"Error concatenating audio segments: {e}")
            # Fallback: just save the first segment
            try:
                with open(output_path, 'wb') as f:
                    f.write(audio_segments[0])
                self.logger.warning("Using first audio segment only due to concatenation error")
            except Exception as fallback_error:
                self.logger.error(f"Failed to save even first audio segment: {fallback_error}")
                raise
            
    def _get_google_tts_voice(self, language: str, voice_name: str = None) -> Dict:
        """Get Google Cloud TTS voice configuration for a language"""
        # Map language codes to Google Cloud TTS voices with extensive Indian language support
        voice_configs = {
            # English
            "en": {
                "language_code": "en-US",
                "voice_name": "en-US-Neural2-C",
                "gender": texttospeech.SsmlVoiceGender.FEMALE
            },
            
            # Major Indian Languages
            "hi": {
                "language_code": "hi-IN", 
                "voice_name": "hi-IN-Neural2-A",
                "gender": texttospeech.SsmlVoiceGender.FEMALE
            },
            "bn": {
                "language_code": "bn-IN",
                "voice_name": "bn-IN-Standard-A", 
                "gender": texttospeech.SsmlVoiceGender.FEMALE
            },
            "te": {
                "language_code": "te-IN",
                "voice_name": "te-IN-Standard-A",
                "gender": texttospeech.SsmlVoiceGender.FEMALE
            },
            "mr": {
                "language_code": "mr-IN", 
                "voice_name": "mr-IN-Standard-A",
                "gender": texttospeech.SsmlVoiceGender.FEMALE
            },
            "ta": {
                "language_code": "ta-IN",
                "voice_name": "ta-IN-Standard-A",
                "gender": texttospeech.SsmlVoiceGender.FEMALE
            },
            "gu": {
                "language_code": "gu-IN",
                "voice_name": "gu-IN-Standard-A", 
                "gender": texttospeech.SsmlVoiceGender.FEMALE
            },
            "ur": {
                "language_code": "ur-IN",
                "voice_name": "ur-IN-Standard-A",
                "gender": texttospeech.SsmlVoiceGender.FEMALE
            },
            "kn": {
                "language_code": "kn-IN",
                "voice_name": "kn-IN-Standard-A",
                "gender": texttospeech.SsmlVoiceGender.FEMALE
            },
            "ml": {
                "language_code": "ml-IN",
                "voice_name": "ml-IN-Standard-A",
                "gender": texttospeech.SsmlVoiceGender.FEMALE
            },
            "pa": {
                "language_code": "pa-IN",
                "voice_name": "pa-IN-Standard-A",
                "gender": texttospeech.SsmlVoiceGender.FEMALE
            },
            
            # International Languages
            "es": {
                "language_code": "es-ES",
                "voice_name": "es-ES-Neural2-A",
                "gender": texttospeech.SsmlVoiceGender.FEMALE
            },
            "fr": {
                "language_code": "fr-FR", 
                "voice_name": "fr-FR-Neural2-A",
                "gender": texttospeech.SsmlVoiceGender.FEMALE
            },
            "de": {
                "language_code": "de-DE",
                "voice_name": "de-DE-Neural2-A",
                "gender": texttospeech.SsmlVoiceGender.FEMALE
            },
            "it": {
                "language_code": "it-IT",
                "voice_name": "it-IT-Neural2-A", 
                "gender": texttospeech.SsmlVoiceGender.FEMALE
            },
            "pt": {
                "language_code": "pt-BR",
                "voice_name": "pt-BR-Neural2-A",
                "gender": texttospeech.SsmlVoiceGender.FEMALE
            },
            "ru": {
                "language_code": "ru-RU",
                "voice_name": "ru-RU-Standard-A",
                "gender": texttospeech.SsmlVoiceGender.FEMALE
            },
            "ja": {
                "language_code": "ja-JP",
                "voice_name": "ja-JP-Neural2-B",
                "gender": texttospeech.SsmlVoiceGender.FEMALE
            },
            "ko": {
                "language_code": "ko-KR",
                "voice_name": "ko-KR-Neural2-A",
                "gender": texttospeech.SsmlVoiceGender.FEMALE
            },
            "zh": {
                "language_code": "cmn-CN",
                "voice_name": "cmn-CN-Standard-A",
                "gender": texttospeech.SsmlVoiceGender.FEMALE
            },
            "ar": {
                "language_code": "ar-XA",
                "voice_name": "ar-XA-Standard-A", 
                "gender": texttospeech.SsmlVoiceGender.FEMALE
            },
            "nl": {
                "language_code": "nl-NL",
                "voice_name": "nl-NL-Standard-A",
                "gender": texttospeech.SsmlVoiceGender.FEMALE
            },
            "sv": {
                "language_code": "sv-SE",
                "voice_name": "sv-SE-Standard-A",
                "gender": texttospeech.SsmlVoiceGender.FEMALE
            }
        }
        
        # Get configuration for the language, fallback to English
        config = voice_configs.get(language, voice_configs["en"])
        
        # Override voice name if specified
        if voice_name:
            config = config.copy()
            config["voice_name"] = voice_name
            
        return config
            
    def generate_multilingual_audio(self, english_text: str, target_language: str, voice_name: str = None) -> Dict:
        """Translate English text to target language and generate audio"""
        try:
            self.logger.info(f"Generating multilingual audio for language: {target_language}")
            
            # Step 1: Translate text if not already in English
            if target_language.lower() != "en":
                translation_result = self.translate_to_language(english_text, target_language)
                if not translation_result["success"]:
                    return {
                        "success": False,
                        "error": f"Translation failed: {translation_result.get('error', 'Unknown error')}",
                        "english_text": english_text,
                        "target_language": target_language
                    }
                text_to_speak = translation_result["translated_text"]
            else:
                text_to_speak = english_text
                translation_result = {
                    "original_text": english_text,
                    "translated_text": english_text,
                    "source_language": "en",
                    "target_language": "en",
                    "success": True
                }
            
            # Step 2: Generate audio
            audio_path = self.text_to_speech(text_to_speak, target_language, voice_name)
            
            # Step 3: Return comprehensive result
            return {
                "success": True,
                "english_text": english_text,
                "translated_text": text_to_speak,
                "target_language": target_language,
                "audio_file": str(audio_path),
                "timestamp": datetime.now().isoformat(),
                "translation_result": translation_result
            }
            
        except Exception as e:
            self.logger.error(f"Error generating multilingual audio: {e}")
            return {
                "success": False,
                "error": str(e),
                "english_text": english_text,
                "target_language": target_language
            }
            
    def process_recording(self, file_path: Path) -> Dict:
        """Process a single recording file"""
        try:
            self.logger.info(f"Processing recording: {file_path.name}")
            
            # First, check if the file is ready (not being actively written)
            if not self.is_file_ready(file_path):
                self.logger.error(f"File {file_path.name} is not ready for processing (still being written or timed out)")
                return {
                    "success": False,
                    "error": "File not ready for processing",
                    "file": str(file_path)
                }
            
            # Convert to WAV if necessary
            if file_path.suffix.lower() != '.wav':
                wav_path = self.convert_audio_to_wav(file_path)
            else:
                wav_path = file_path
            
            # Transcribe audio
            transcription_result = self.transcribe_audio(wav_path)
            
            if not transcription_result["transcript"]:
                self.logger.warning(f"No transcript generated for {file_path.name}")
                return {
                    "success": False,
                    "error": "No transcript generated",
                    "file": str(file_path),
                    "transcription_error": transcription_result.get("error", "Unknown error")
                }
            
            # Translate if not in English
            if self.config["translation_enabled"] and transcription_result["language"] != self.config["target_language"]:
                translation_result = self.translate_text(
                    transcription_result["transcript"],
                    transcription_result["language"],
                    self.config["target_language"]
                )
            else:
                translation_result = {
                    "translated_text": transcription_result["transcript"],
                    "source_language": transcription_result["language"],
                    "target_language": self.config["target_language"],
                    "success": True
                }
            
            # Save results
            result = {
                "file_path": str(file_path),
                "timestamp": datetime.now().isoformat(),
                "transcription": transcription_result,
                "translation": translation_result,
                "success": True
            }
            
            # Save transcript to file
            transcript_filename = f"{file_path.stem}_transcript.json"
            transcript_path = self.transcripts_dir / transcript_filename
            
            with open(transcript_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"Successfully processed {file_path.name}")
            self.logger.info(f"Transcript: '{transcription_result['transcript'][:100]}...'")
            if translation_result.get("translated_text") != transcription_result["transcript"]:
                self.logger.info(f"Translation: '{translation_result['translated_text'][:100]}...'")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error processing {file_path.name}: {e}")
            return {
                "success": False,
                "error": str(e),
                "file": str(file_path)
            }
            
    def process_existing_files(self):
        """Process all existing unprocessed files"""
        self.logger.info("Processing existing files...")
        
        processed_count = 0
        for monitor_dir in self.config["monitoring_directories"]:
            monitor_path = Path(monitor_dir)
            if monitor_path.exists():
                for file_path in monitor_path.iterdir():
                    if (file_path.is_file() and 
                        file_path.suffix.lower() in self.config["audio_formats"] and
                        str(file_path) not in self.processed_files):
                        
                        try:
                            result = self.process_recording(file_path)
                            if result["success"]:
                                self.processed_files.append(str(file_path))
                                processed_count += 1
                        except Exception as e:
                            self.logger.error(f"Error processing existing file {file_path.name}: {e}")
                        
        self.save_processed_files()
        self.logger.info(f"Processed {processed_count} existing files")
        
    def start_monitoring(self):
        """Start monitoring directories for new files"""
        self.logger.info("Starting file monitoring...")
        self.running = True
        
        # Process existing files first
        self.process_existing_files()
        
        # Set up file system watchers
        event_handler = RecordingFileHandler(self)
        observer = Observer()
        
        for monitor_dir in self.config["monitoring_directories"]:
            monitor_path = Path(monitor_dir)
            if monitor_path.exists():
                observer.schedule(event_handler, str(monitor_path), recursive=False)
                self.logger.info(f"Monitoring directory: {monitor_path}")
            else:
                self.logger.warning(f"Monitor directory does not exist: {monitor_path}")
                
        observer.start()
        
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("Received keyboard interrupt")
        finally:
            observer.stop()
            observer.join()
            self.logger.info("File monitoring stopped")
            
    def stop_monitoring(self):
        """Stop monitoring"""
        self.running = False


class RecordingFileHandler(FileSystemEventHandler):
    """File system event handler for new recordings"""
    
    def __init__(self, processor: RecordingProcessorGoogle):
        self.processor = processor
        self.pending_files = {}  # Track files that might still be being written
        
    def on_created(self, event):
        """Handle file creation events"""
        if event.is_directory:
            return
            
        file_path = Path(event.src_path)
        
        # Check if it's an audio file we care about
        if file_path.suffix.lower() in self.processor.config["audio_formats"]:
            self.processor.logger.info(f"New audio file detected: {file_path.name}")
            # Schedule processing after delay to ensure file is complete
            timer = threading.Timer(self.processor.config["processing_delay"], self._process_file_delayed, [file_path])
            timer.start()
            
    def _process_file_delayed(self, file_path: Path):
        """Process file after checking it's completely written"""
        if file_path.exists():
            try:
                # Check if file is ready before processing
                if self.processor.is_file_ready(file_path):
                    result = self.processor.process_recording(file_path)
                    if result["success"]:
                        self.processor.processed_files.append(str(file_path))
                        self.processor.save_processed_files()
                else:
                    self.processor.logger.warning(f"File {file_path.name} was not ready for processing")
            except Exception as e:
                self.processor.logger.error(f"Error processing new file {file_path.name}: {e}")


def signal_handler(signum, frame):
    """Handle interrupt signals"""
    print("\nReceived interrupt signal. Shutting down gracefully...")
    global processor
    if processor:
        processor.stop_monitoring()
    sys.exit(0)


def main():
    """Main function"""
    global processor
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == '--status':
            show_status()
            return
        elif sys.argv[1] == '--test':
            test_credentials()
            return
        elif sys.argv[1] == '--help':
            show_help()
            return
    
    try:
        # Initialize processor
        processor = RecordingProcessorGoogle()
        
        print("Recording Processor Started (AssemblyAI + Google Cloud)")
        print("Press Ctrl+C to stop")
        print("-" * 50)
        
        # Start monitoring
        processor.start_monitoring()
        
    except Exception as e:
        print(f"Error starting processor: {e}")
        import traceback
        traceback.print_exc()


def show_status():
    """Show current status of the recording processor"""
    base_dir = Path('/Users/apple/Desktop/asterisk')
    recordings_dir = base_dir / 'recordings'
    
    print("🎯 Recording Processor Status")
    print("=" * 50)
    
    # Check directories
    print("\n📁 Directories:")
    dirs_to_check = {
        'Monitor': base_dir / 'monitor',
        'Raw': recordings_dir / 'raw',
        'Converted': recordings_dir / 'converted',
        'Transcripts': recordings_dir / 'transcripts',
        'Generated Audio': recordings_dir / 'generated_audio'
    }
    
    for name, path in dirs_to_check.items():
        if path.exists():
            file_count = len([f for f in path.iterdir() if f.is_file()])
            print(f"  ✅ {name}: {file_count} files")
        else:
            print(f"  ❌ {name}: Directory not found")
    
    # Check processed files
    processed_file_path = recordings_dir / 'processed_files.json'
    if processed_file_path.exists():
        try:
            with open(processed_file_path, 'r') as f:
                processed_files = json.load(f)
            print(f"\n📊 Processed files: {len(processed_files)}")
        except:
            print("\n📊 Processed files: Error reading file")
    else:
        print("\n📊 Processed files: 0 (no tracking file)")
    
    # Check recent transcripts
    transcripts_dir = recordings_dir / 'transcripts'
    if transcripts_dir.exists():
        transcript_files = sorted(
            [f for f in transcripts_dir.iterdir() if f.suffix == '.json'],
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )
        
        print(f"\n📝 Recent transcripts ({min(5, len(transcript_files))}):")
        for transcript_file in transcript_files[:5]:
            try:
                mod_time = datetime.fromtimestamp(transcript_file.stat().st_mtime)
                print(f"  • {transcript_file.name} ({mod_time.strftime('%Y-%m-%d %H:%M:%S')})")
            except:
                print(f"  • {transcript_file.name}")
    
    # Check environment configuration
    print(f"\n⚙️ Environment:")
    env_file = base_dir / '.env'
    if env_file.exists():
        print(f"  ✅ .env file found")
        # Check key environment variables
        with open(env_file, 'r') as f:
            env_content = f.read()
            if 'GOOGLE_CLOUD_API_KEY=' in env_content and 'your_api_key_here' not in env_content:
                print(f"  ✅ Google Cloud API key configured")
            else:
                print(f"  ❌ Google Cloud API key not configured")
    else:
        print(f"  ❌ .env file not found")
    
    print("\n" + "=" * 50)


def test_credentials():
    """Test Google Cloud Speech-to-Text and translation services"""
    print("🧪 Testing Google Cloud Speech-to-Text and Translation Services...")
    
    try:
        # Load environment variables
        load_dotenv()
        
        # Test initialization
        processor = RecordingProcessorGoogle()
        print("✅ Google Cloud Speech-to-Text and Translation services initialized successfully")
        
        # Test each service
        print("\n🔍 Testing individual services:")
        
        # Test Google Cloud Speech-to-Text
        try:
            if processor.speech_client:
                print("  ✅ Google Cloud Speech-to-Text: Client initialized")
            else:
                print("  ❌ Google Cloud Speech-to-Text: Client not initialized")
        except Exception as e:
            print(f"  ❌ Google Cloud Speech-to-Text: {e}")
        
        # Test Translation Services
        print("\n📝 Testing translation services:")
        
        test_text = "Hello, how are you?"
        
        # Test free translation services
        if DEEP_TRANSLATOR_AVAILABLE:
            print("  ✅ deep-translator library: Available")
            
            # Test free Google Translate
            try:
                result = processor._translate_with_free_google(test_text, "en", "es")
                if result["success"]:
                    print(f"  ✅ Free Google Translate: '{result['translated_text']}'")
                else:
                    print(f"  ❌ Free Google Translate: {result.get('error', 'Failed')}")
            except Exception as e:
                print(f"  ❌ Free Google Translate: {e}")
            
            # Test MyMemory
            try:
                result = processor._translate_with_mymemory(test_text, "en", "es")
                if result["success"]:
                    print(f"  ✅ MyMemory API: '{result['translated_text']}'")
                else:
                    print(f"  ⚠️ MyMemory API: {result.get('error', 'Failed')}")
            except Exception as e:
                print(f"  ❌ MyMemory API: {e}")
            
            # Test LibreTranslate
            try:
                result = processor._translate_with_libre(test_text, "en", "es")
                if result["success"]:
                    print(f"  ✅ LibreTranslate: '{result['translated_text']}'")
                else:
                    print(f"  ⚠️ LibreTranslate: {result.get('error', 'Failed')}")
            except Exception as e:
                print(f"  ❌ LibreTranslate: {e}")
                
        else:
            print("  ❌ deep-translator library: Not installed")
            print("      Install with: pip install deep-translator")
        
        # Test Google Cloud Translation
        try:
            if processor.translate_client:
                result = processor._translate_with_google_cloud(test_text, "en", "es")
                if result["success"]:
                    print(f"  ✅ Google Cloud Translation: '{result['translated_text']}'")
                else:
                    print(f"  ❌ Google Cloud Translation: {result.get('error', 'Failed')}")
            else:
                print("  ⚠️ Google Cloud Translation: No credentials configured")
        except Exception as e:
            print(f"  ❌ Google Cloud Translation: {e}")
        
        # Test Text-to-Speech
        try:
            if processor.tts_client:
                print("  ✅ Text-to-Speech: Client created")
            else:
                print("  ⚠️ Text-to-Speech: No credentials configured")
        except Exception as e:
            print(f"  ❌ Text-to-Speech: {e}")
        
        print("\n🎉 Testing completed!")
        
        if DEEP_TRANSLATOR_AVAILABLE:
            print("\n💡 You have access to multiple free translation services!")
        else:
            print("\n💡 Install deep-translator for free translation services:")
            print("   pip install deep-translator")
        
        # Test Hindi speech recognition configuration
        print(f"\n🇮🇳 Hindi Speech Recognition Configuration:")
        print(f"  Primary language: {processor.primary_language}")
        print(f"  Auto language detection: {processor.auto_detect}")
        print(f"  Speech model: {processor.speech_model}")
        
    except Exception as e:
        print(f"❌ Testing failed: {e}")
        print("\nPlease check your configuration:")
        print("  - GOOGLE_CLOUD_API_KEY or GOOGLE_APPLICATION_CREDENTIALS should be set")
        print("  - PRIMARY_LANGUAGE (default: hi-IN for Hindi)")
        print("  - Install deep-translator: pip install deep-translator")


def show_help():
    """Show help information"""
    print("""
🎯 Asterisk Recording Processor - Google Cloud Speech-to-Text + Multiple Translation APIs

Usage:
  python recording_processor_google.py [OPTIONS]

Options:
  --status    Show current system status
  --test      Test Google Cloud Speech-to-Text and translation services
  --help      Show this help message

Default (no options):
  Start monitoring for new recordings and process them automatically

Features:
  • 🎤 Speech-to-text using Google Cloud Speech-to-Text (with Hindi language support)
  • 👥 Speaker diarization (identify different speakers)
  • 🌍 Auto language detection with Hindi as primary language
  • ⏱️ Smart handling of long audio files (>1 minute) using async recognition
  • 🔄 Multiple translation services with automatic fallback:
    - Free Google Translate (via deep-translator)
    - MyMemory API (free, generous limits)
    - LibreTranslate (open source)
    - Google Cloud Translation (paid, most accurate)
    - PONS Dictionary (good for phrases)
  • 🔊 Text-to-speech using Google Cloud TTS with Hindi voice support
  • 📁 Real-time file monitoring
  • 🐳 Docker container support

Configuration:
  Edit .env file to configure APIs
  
Required API Keys:
  • GOOGLE_CLOUD_API_KEY or GOOGLE_APPLICATION_CREDENTIALS - for speech recognition, translation and TTS (required)
  
Optional Configuration:
  • PRIMARY_LANGUAGE - default language for speech recognition (default: hi-IN for Hindi)
  • SPEECH_TO_TEXT_MODEL - Google Cloud speech model (default: latest_long)
  • LANGUAGE_AUTO_DETECT - enable automatic language detection (default: true)
  • TRANSLATION_SERVICES - comma-separated preference order
    (default: "free_google,mymemory,libretranslate,google_cloud,pons")

Audio Handling:
  • Automatically converts audio to WAV format for Google Cloud recognition
  • Handles long audio files (>1 minute) using asynchronous processing
  • Chunked processing fallback for very long files
  • Supports multiple input formats: .ulaw, .wav, .gsm, .mp3, .flac

Installation:
  pip install google-cloud-speech google-cloud-translate google-cloud-texttospeech
  pip install deep-translator  # For free translation services
  
Monitoring directories:
  • ./recordings/raw/
  • ./monitor/
  • Docker container paths (when running in container)

Output directories:
  • ./recordings/transcripts/ (JSON transcripts with speaker info and Hindi support)
  • ./recordings/converted/ (converted FLAC audio files)
  • ./recordings/generated_audio/ (TTS output with Hindi voice support)

Google Cloud Speech Models:
  • latest_long: Optimized for longer audio files (default)
  • latest_short: Optimized for shorter audio files
  • phone_call: Optimized for phone call audio quality

Hindi Language Support:
  • Primary language: hi-IN (Hindi - India)
  • Alternative languages: en-US, en-IN for mixed language detection
  • Enhanced phrase recognition for common Hindi words
  • Text-to-speech output in Hindi using Google's neural voices

Translation Services:
  • free_google: Free Google Translate (5000 chars/request)
  • mymemory: MyMemory API (10000 chars/day free)
  • libretranslate: Open source, self-hosted option
  • google_cloud: Google Cloud Translation (paid, most accurate)
  • pons: PONS Dictionary (good for short phrases)
""")


if __name__ == "__main__":
    main()
