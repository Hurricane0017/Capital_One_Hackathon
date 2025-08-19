#!/usr/bin/env python3
"""
Transcript Monitor - Real-time IVR Processing
Monitors the transcripts directory for new incoming transcript files and processes them through the orchestrator agent.

This script:
1. Continuously monitors the transcripts directory for new JSON files
2. Extracts translated text from new transcript files
3. Calls the orchestrator agent with the translated text
4. Logs all processing activities
5. Handles errors gracefully and continues monitoring

Key Features:
- Real-time file monitoring using watchdog
- Automatic transcript processing
- Orchestrator agent integration
- Comprehensive logging
- Error handling and recovery

Author: AI Assistant
Date: August 18, 2025
"""

import os
import sys
import json
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Set
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Add the Capital-One-Competition directory to Python path for imports
script_dir = os.path.dirname(os.path.abspath(__file__))
competition_dir = os.path.join(script_dir, "Capital-One-Competition")
src_dir = os.path.join(script_dir, "src")
sys.path.append(competition_dir)
sys.path.append(src_dir)

try:
    from orchestrator_agent import OrchestratorAgent
    from logging_config import setup_logging
    from recording_processor import RecordingProcessorGoogle
except ImportError as e:
    print(f"❌ Error importing orchestrator components: {e}")
    print("🔧 Make sure you're running this script from the asterisk directory")
    sys.exit(1)

# Configuration
TRANSCRIPTS_DIR = "/Users/apple/Desktop/asterisk/recordings/transcripts"
DEFAULT_PHONE = "9876001234"  # Default phone number for testing
PROCESSED_FILES_LOG = "/Users/apple/Desktop/asterisk/recordings/processed_transcripts.json"

# Setup logging
logger = setup_logging('TranscriptMonitor')

class TranscriptMonitor(FileSystemEventHandler):
    """
    File system event handler for monitoring transcript files.
    """
    
    def __init__(self):
        """Initialize the transcript monitor."""
        super().__init__()
        self.processed_files: Set[str] = self._load_processed_files()
        self.orchestrator = None
        self.tts_processor = None
        self._initialize_orchestrator()
        self._initialize_tts_processor()
        
        logger.info("🎯 Transcript Monitor initialized")
        logger.info(f"📁 Monitoring directory: {TRANSCRIPTS_DIR}")
        logger.info(f"📱 Default phone number: {DEFAULT_PHONE}")
    
    def _initialize_orchestrator(self):
        """Initialize the orchestrator agent."""
        try:
            logger.info("🤖 Initializing Orchestrator Agent...")
            self.orchestrator = OrchestratorAgent()
            logger.info("✅ Orchestrator Agent initialized successfully")
            logger.info("🔑 Note: If you get 401 errors, check the OpenRouter API key in llm_client.py")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Orchestrator Agent: {e}")
            self.orchestrator = None
    
    def _initialize_tts_processor(self):
        """Initialize the TTS processor with Google Cloud Translation API priority."""
        try:
            logger.info("🔊 Initializing TTS Processor with Google Cloud Translation API...")
            self.tts_processor = RecordingProcessorGoogle()
            logger.info("✅ TTS Processor initialized successfully")
            logger.info("🌍 Google Cloud Translation API will be prioritized for text translation")
        except Exception as e:
            logger.error(f"❌ Failed to initialize TTS Processor: {e}")
            self.tts_processor = None
    
    def _load_processed_files(self) -> Set[str]:
        """Load the list of already processed files."""
        try:
            if os.path.exists(PROCESSED_FILES_LOG):
                with open(PROCESSED_FILES_LOG, 'r') as f:
                    data = json.load(f)
                    return set(data.get('processed_files', []))
        except Exception as e:
            logger.warning(f"⚠️ Could not load processed files log: {e}")
        
        return set()
    
    def _save_processed_files(self):
        """Save the list of processed files."""
        try:
            data = {
                'processed_files': list(self.processed_files),
                'last_updated': datetime.now().isoformat()
            }
            with open(PROCESSED_FILES_LOG, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"❌ Could not save processed files log: {e}")
    
    def on_created(self, event):
        """Handle file creation events."""
        if not event.is_directory and event.src_path.endswith('.json'):
            self._process_transcript_file(event.src_path)
    
    def on_modified(self, event):
        """Handle file modification events."""
        if not event.is_directory and event.src_path.endswith('.json'):
            # Only process if we haven't seen this file before
            filename = os.path.basename(event.src_path)
            if filename not in self.processed_files:
                self._process_transcript_file(event.src_path)
    
    def _process_transcript_file(self, file_path: str):
        """
        Process a new transcript file.
        
        Args:
            file_path (str): Path to the transcript JSON file
        """
        filename = os.path.basename(file_path)
        
        # Skip if already processed
        if filename in self.processed_files:
            logger.debug(f"📄 File {filename} already processed, skipping")
            return
        
        logger.info(f"📄 Processing new transcript file: {filename}")
        
        try:
            # Wait a moment for file to be fully written
            time.sleep(1)
            
            # Read and parse the transcript file
            transcript_data = self._read_transcript_file(file_path)
            if not transcript_data:
                return
            
            # Extract translated text
            translated_text = self._extract_translated_text(transcript_data)
            if not translated_text:
                logger.warning(f"⚠️ No translated text found in {filename}")
                return
            
            # Process through orchestrator
            response = self._process_with_orchestrator(translated_text, filename)
            
            # Generate audio response if orchestrator succeeded
            if response and not self._is_error_response(response):
                self._generate_audio_response(response, translated_text, filename)
            else:
                logger.warning("⚠️ Skipping audio generation due to orchestrator error or empty response")
            
            # Mark as processed
            self.processed_files.add(filename)
            self._save_processed_files()
            
            logger.info(f"✅ Successfully processed {filename}")
            
        except Exception as e:
            logger.error(f"❌ Error processing {filename}: {e}")
    
    def _is_error_response(self, response: str) -> bool:
        """
        Check if a response is an error message.
        
        Args:
            response (str): The response to check
            
        Returns:
            bool: True if the response appears to be an error message
        """
        if not isinstance(response, str):
            return True
        
        response_lower = response.lower().strip()
        error_indicators = [
            "error:",
            "failed",
            "exception",
            "unauthorized",
            "not found",
            "invalid",
            "timeout"
        ]
        
        # Check if response is too short (likely an error)
        if len(response_lower) < 20:
            return True
        
        # Check for error indicators
        for indicator in error_indicators:
            if indicator in response_lower:
                return True
        
        return False
    
    def _read_transcript_file(self, file_path: str) -> Dict[str, Any]:
        """
        Read and parse a transcript JSON file.
        
        Args:
            file_path (str): Path to the transcript file
            
        Returns:
            Dict[str, Any]: Parsed transcript data or None if error
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            logger.debug(f"📖 Successfully read transcript file: {os.path.basename(file_path)}")
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON in {file_path}: {e}")
            return None
        except FileNotFoundError:
            logger.error(f"❌ File not found: {file_path}")
            return None
        except Exception as e:
            logger.error(f"❌ Error reading {file_path}: {e}")
            return None
    
    def _extract_translated_text(self, transcript_data: Dict[str, Any]) -> str:
        """
        Extract translated text from transcript data.
        
        Args:
            transcript_data (Dict[str, Any]): Parsed transcript data
            
        Returns:
            str: Translated text or None if not found
        """
        try:
            # Check if the transcript was successful
            if not transcript_data.get('success', False):
                logger.warning("⚠️ Transcript processing was not successful")
                return None
            
            # Extract translated text from the expected structure
            translation = transcript_data.get('translation', {})
            if not translation.get('success', False):
                logger.warning("⚠️ Translation was not successful")
                # Fallback to original transcript if translation failed
                transcription = transcript_data.get('transcription', {})
                return transcription.get('transcript', '')
            
            translated_text = translation.get('translated_text', '').strip()
            
            if not translated_text:
                # Fallback to original transcript
                transcription = transcript_data.get('transcription', {})
                translated_text = transcription.get('transcript', '').strip()
            
            logger.info(f"📝 Extracted text: '{translated_text}'")
            return translated_text
            
        except Exception as e:
            logger.error(f"❌ Error extracting translated text: {e}")
            return None
    
    def _process_with_orchestrator(self, translated_text: str, filename: str) -> str:
        """
        Process the translated text through the orchestrator agent.
        
        Args:
            translated_text (str): The translated farmer input
            filename (str): Original filename for reference
            
        Returns:
            str: The orchestrator response or None if failed
        """
        if not self.orchestrator:
            logger.error("❌ Orchestrator not available, attempting to reinitialize...")
            self._initialize_orchestrator()
            if not self.orchestrator:
                logger.error("❌ Could not initialize orchestrator, skipping processing")
                return None
        
        try:
            logger.info(f"🌾 Processing farmer input through orchestrator...")
            logger.info(f"📱 Using phone: {DEFAULT_PHONE}")
            logger.info(f"💬 Input: '{translated_text}'")
            
            # Call the orchestrator agent
            response = self.orchestrator.process_farmer_request(
                raw_farmer_input=translated_text,
                farmer_phone=DEFAULT_PHONE
            )
            
            # Check if the response is an error message
            if isinstance(response, str) and (
                response.startswith("Error:") or 
                "error" in response.lower() or 
                "failed" in response.lower() or
                len(response.strip()) < 10  # Very short responses are likely errors
            ):
                logger.error(f"❌ Orchestrator returned an error response: {response}")
                logger.error("❌ This suggests an authentication or configuration issue with the LLM service")
                return None
            
            logger.info("✅ Orchestrator processing completed")
            logger.info(f"📤 Response length: {len(response)} characters")
            logger.info(f"📤 Response preview: {response[:200]}...")
            
            # Save the response
            self._save_response(translated_text, response, filename)
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Error processing with orchestrator: {e}")
            logger.exception("Full error traceback:")
            return None
    
    def _save_response(self, input_text: str, response: str, filename: str):
        """
        Save the orchestrator response to a file.
        
        Args:
            input_text (str): Original farmer input
            response (str): Orchestrator response
            filename (str): Original transcript filename
        """
        try:
            # Create responses directory if it doesn't exist
            responses_dir = "/Users/apple/Desktop/asterisk/recordings/responses"
            os.makedirs(responses_dir, exist_ok=True)
            
            # Create response filename
            base_name = filename.replace('_transcript.json', '')
            response_filename = f"{base_name}_response.json"
            response_path = os.path.join(responses_dir, response_filename)
            
            # Prepare response data
            response_data = {
                "timestamp": datetime.now().isoformat(),
                "original_transcript_file": filename,
                "farmer_input": input_text,
                "farmer_phone": DEFAULT_PHONE,
                "orchestrator_response": response,
                "processing_metadata": {
                    "processed_by": "TranscriptMonitor",
                    "version": "1.0"
                }
            }
            
            # Save response
            with open(response_path, 'w', encoding='utf-8') as f:
                json.dump(response_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"💾 Response saved to: {response_filename}")
            
        except Exception as e:
            logger.error(f"❌ Error saving response: {e}")
    
    def _generate_audio_response(self, response_text: str, original_input: str, filename: str):
        """
        Generate audio response using TTS after translating the orchestrator's response to Hindi.
        
        Args:
            response_text (str): The orchestrator's text response (in English)
            original_input (str): The original farmer input for context
            filename (str): Original transcript filename for reference
        """
        if not self.tts_processor:
            logger.error("❌ TTS Processor not available, attempting to reinitialize...")
            self._initialize_tts_processor()
            if not self.tts_processor:
                logger.error("❌ Could not initialize TTS processor, skipping audio generation")
                return
        
        try:
            logger.info("🔊 Generating audio response...")
            logger.info(f"📝 English response: '{response_text[:100]}...'")
            
            # Translate the English response to Hindi using Google Cloud Translation API
            logger.info("🌍 Translating response to Hindi using Google Cloud Translation API...")
            translation_result = self.tts_processor.translate_text(
                text=response_text,
                source_lang="en",  # Orchestrator response is in English
                target_lang="hi"   # Translate to Hindi for the farmer
            )
            
            if translation_result.get('success', False):
                hindi_text = translation_result['translated_text']
                logger.info(f"✅ Translation successful using {translation_result.get('service', 'unknown')}")
                logger.info(f"📝 Hindi text: '{hindi_text[:100]}...'")
            else:
                logger.warning(f"⚠️ Translation failed: {translation_result.get('error', 'Unknown error')}")
                logger.info("🔄 Using original English text for audio generation")
                hindi_text = response_text
            
            # Generate audio in Hindi
            result = self.tts_processor.generate_multilingual_audio(
                english_text=hindi_text,  # Now contains Hindi text (or English as fallback)
                target_language="hi"      # Generate Hindi audio
            )
            
            if result['success']:
                logger.info("✅ Audio response generated successfully!")
                logger.info(f"🎵 Audio file: {result['audio_file']}")
                logger.info(f"🌍 Language: {result['target_language']}")
                
                # Save additional metadata about the audio response
                self._save_audio_metadata(result, response_text, hindi_text, original_input, filename)
                
                # Copy to a more accessible location for playback
                self._copy_audio_for_playback(result['audio_file'], filename)
                
            else:
                logger.error(f"❌ Failed to generate audio: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            logger.error(f"❌ Error generating audio response: {e}")
            logger.exception("Full error traceback:")
    
    def _save_audio_metadata(self, audio_result: Dict[str, Any], english_response: str, 
                           hindi_response: str, original_input: str, filename: str):
        """
        Save metadata about the generated audio response.
        
        Args:
            audio_result (Dict[str, Any]): Result from TTS generation
            english_response (str): The original English orchestrator response
            hindi_response (str): The translated Hindi response
            original_input (str): Original farmer input
            filename (str): Original transcript filename
        """
        try:
            # Create audio metadata directory
            metadata_dir = "/Users/apple/Desktop/asterisk/recordings/audio_metadata"
            os.makedirs(metadata_dir, exist_ok=True)
            
            # Create metadata filename
            base_name = filename.replace('_transcript.json', '')
            metadata_filename = f"{base_name}_audio_metadata.json"
            metadata_path = os.path.join(metadata_dir, metadata_filename)
            
            # Prepare metadata
            metadata = {
                "timestamp": datetime.now().isoformat(),
                "original_transcript_file": filename,
                "farmer_input": original_input,
                "orchestrator_response": {
                    "english": english_response,
                    "hindi": hindi_response
                },
                "audio_generation": {
                    "success": audio_result['success'],
                    "audio_file": audio_result['audio_file'],
                    "target_language": audio_result['target_language'],
                    "translated_text": audio_result.get('translated_text', hindi_response),
                    "processing_time": audio_result.get('processing_time', 'unknown')
                },
                "translation_metadata": {
                    "english_to_hindi": True,
                    "translation_service": "google_cloud",
                    "source_language": "en",
                    "target_language": "hi"
                },
                "processing_metadata": {
                    "processed_by": "TranscriptMonitor",
                    "version": "2.0",
                    "tts_enabled": True,
                    "google_cloud_translation": True
                }
            }
            
            # Save metadata
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            logger.info(f"💾 Audio metadata saved to: {metadata_filename}")
            
        except Exception as e:
            logger.error(f"❌ Error saving audio metadata: {e}")
    
    def _copy_audio_for_playback(self, audio_file_path: str, original_filename: str):
        """
        Copy the generated audio to a playback directory for easy access.
        
        Args:
            audio_file_path (str): Path to the generated audio file
            original_filename (str): Original transcript filename for reference
        """
        try:
            import shutil
            
            # Create playback directory
            playback_dir = "/Users/apple/Desktop/asterisk/recordings/generated_audio"
            os.makedirs(playback_dir, exist_ok=True)
            
            # Create playback filename
            base_name = original_filename.replace('_transcript.json', '')
            playback_filename = f"{base_name}_response.wav"
            playback_path = os.path.join(playback_dir, playback_filename)
            
            # Copy the file
            shutil.copy2(audio_file_path, playback_path)
            
            logger.info(f"🎵 Audio copied for playback: {playback_filename}")
            logger.info(f"📁 Playback location: {playback_dir}")
            
        except Exception as e:
            logger.error(f"❌ Error copying audio for playback: {e}")

def monitor_transcripts():
    """
    Main function to start monitoring the transcripts directory.
    """
    logger.info("🚀 Starting Transcript Monitor")
    logger.info("=" * 50)
    
    # Check if transcripts directory exists
    if not os.path.exists(TRANSCRIPTS_DIR):
        logger.error(f"❌ Transcripts directory does not exist: {TRANSCRIPTS_DIR}")
        return
    
    # Process any existing files first
    logger.info("🔍 Checking for existing files...")
    monitor = TranscriptMonitor()
    
    existing_files = [f for f in os.listdir(TRANSCRIPTS_DIR) if f.endswith('.json')]
    logger.info(f"📄 Found {len(existing_files)} existing files")
    
    for filename in existing_files:
        if filename not in monitor.processed_files:
            file_path = os.path.join(TRANSCRIPTS_DIR, filename)
            logger.info(f"📄 Processing existing file: {filename}")
            monitor._process_transcript_file(file_path)
    
    # Start watching for new files
    logger.info("👀 Starting file system monitoring...")
    
    observer = Observer()
    observer.schedule(monitor, TRANSCRIPTS_DIR, recursive=False)
    observer.start()
    
    try:
        logger.info("✅ Transcript Monitor is running")
        logger.info(f"📁 Watching: {TRANSCRIPTS_DIR}")
        logger.info("🔄 Waiting for new transcript files...")
        logger.info("Press Ctrl+C to stop")
        
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("🛑 Stopping Transcript Monitor...")
        observer.stop()
    
    observer.join()
    logger.info("✅ Transcript Monitor stopped")

if __name__ == "__main__":
    print("🎯 TRANSCRIPT MONITOR - IVR Processing")
    print("=" * 50)
    print("🌟 Real-time transcript processing with Orchestrator Agent")
    print("=" * 50)
    
    try:
        monitor_transcripts()
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)
