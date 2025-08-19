#!/usr/bin/env python3
"""
Audio File Fetcher and Processor
Monitors the monitor directory for new audio files, processes them using the recording processor,
and saves transcripts to the transcripts directory.
"""

import os
import time
import json
import shutil
import logging
from datetime import datetime
from pathlib import Path
import sys

# Import the recording processor
try:
    from recording_processor import RecordingProcessorGoogle
except ImportError:
    # If not found, try importing from current directory
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from recording_processor import RecordingProcessorGoogle

class AudioFetcher:
    """Audio file fetcher and processor for monitoring directories and processing recordings"""
    
    def __init__(self):
        # Setup base directories
        self.base_dir = Path("/Users/apple/Desktop/asterisk")
        self.monitor_dir = self.base_dir / "monitor"
        self.recordings_dir = self.base_dir / "recordings"
        self.transcripts_dir = self.recordings_dir / "transcripts"
        self.converted_dir = self.recordings_dir / "converted"
        
        # Log file
        self.log_file = self.recordings_dir / "fetcher.log"
        self.processed_file = self.recordings_dir / "processed_files.json"
        
        # Supported audio formats (especially Asterisk formats)
        self.audio_formats = {'.wav', '.mp3', '.gsm', '.ulaw', '.alaw', '.sln', '.g722', '.au'}
        
        # Create required directories
        for directory in [self.recordings_dir, self.transcripts_dir, self.converted_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Setup logging
        self.setup_logging()
        
        # Load processed files
        self.processed_files = self.load_processed_files()
        
        # Initialize recording processor
        self.recording_processor = None
        self.init_recording_processor()
        
        self.logger.info("Audio Fetcher and Processor initialized")
        self.logger.info(f"Monitor directory: {self.monitor_dir}")
        self.logger.info(f"Transcripts directory: {self.transcripts_dir}")
    
    def init_recording_processor(self):
        """Initialize the recording processor"""
        try:
            self.recording_processor = RecordingProcessorGoogle()
            self.logger.info("Recording processor initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize recording processor: {e}")
            self.logger.warning("Proceeding without recording processor - files will only be copied")
    
    def setup_logging(self):
        """Setup logging configuration"""
        # Ensure recordings directory exists for log file
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('AudioFetcher')
    
    def load_processed_files(self):
        """Load list of already processed files"""
        try:
            if self.processed_file.exists():
                with open(self.processed_file, 'r') as f:
                    data = json.load(f)
                return set(data.get('files', []))
        except Exception as e:
            self.logger.warning(f"Could not load processed files: {e}")
        return set()
    
    def save_processed_files(self):
        """Save list of processed files"""
        try:
            data = {
                'files': list(self.processed_files),
                'last_updated': datetime.now().isoformat(),
                'count': len(self.processed_files)
            }
            with open(self.processed_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            self.logger.error(f"Could not save processed files: {e}")
    
    def is_audio_file(self, filepath):
        """Check if file is an audio file"""
        return filepath.suffix.lower() in self.audio_formats
    
    def is_file_ready(self, filepath, stability_time=5, max_wait=120):
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
    
    def find_new_audio_files(self):
        """Find new audio files in the monitor directory"""
        new_files = []
        
        if not self.monitor_dir.exists():
            self.logger.warning(f"Monitor directory does not exist: {self.monitor_dir}")
            return new_files
                
        try:
            # Search for audio files in monitor directory
            for file_path in self.monitor_dir.iterdir():
                if (file_path.is_file() and 
                    self.is_audio_file(file_path) and 
                    str(file_path) not in self.processed_files):
                    new_files.append(file_path)
        except Exception as e:
            self.logger.error(f"Error scanning {self.monitor_dir}: {e}")
        
        return new_files
    
    def process_audio_file(self, source_path):
        """Process audio file using the recording processor and save to transcripts"""
        try:
            self.logger.info(f"Processing audio file: {source_path.name}")
            
            # First, check if the file is ready (not being actively written)
            if not self.is_file_ready(source_path):
                self.logger.error(f"File {source_path.name} is not ready for processing (still being written or timed out)")
                return False
            
            # Check if recording processor is available
            if not self.recording_processor:
                self.logger.warning("Recording processor not available, skipping processing")
                return False
            
            # Process the recording
            result = self.recording_processor.process_recording(source_path)
            
            if result.get("success", False):
                self.logger.info(f"Successfully processed {source_path.name}")
                
                # Clean up completion marker file if it exists
                completion_marker = source_path.with_suffix('.complete')
                if completion_marker.exists():
                    try:
                        completion_marker.unlink()
                        self.logger.info(f"Removed completion marker for {source_path.name}")
                    except Exception as e:
                        self.logger.warning(f"Could not remove completion marker: {e}")
                
                # Mark as processed
                self.processed_files.add(str(source_path))
                
                # Log processing details
                if "transcription" in result:
                    transcript = result["transcription"].get("transcript", "")[:100]  # First 100 chars
                    language = result["transcription"].get("language", "unknown")
                    self.logger.info(f"Transcript preview ({language}): {transcript}...")
                
                return True
            else:
                error_msg = result.get("error", "Unknown error")
                self.logger.error(f"Failed to process {source_path.name}: {error_msg}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error processing {source_path}: {e}")
            return False
    
    def fetch_files_once(self):
        """Perform one scan and process new files"""
        self.logger.info("Scanning for new audio files in monitor directory...")
        
        new_files = self.find_new_audio_files()
        
        if not new_files:
            self.logger.info("No new audio files found")
            return 0
        
        self.logger.info(f"Found {len(new_files)} new audio files")
        
        processed_count = 0
        for file_path in new_files:
            if self.process_audio_file(file_path):
                processed_count += 1
        
        # Save processed files list
        self.save_processed_files()
        
        self.logger.info(f"Successfully processed {processed_count} files")
        return processed_count
    
    def run_continuous(self, interval=30):
        """Run continuous monitoring"""
        self.logger.info(f"Starting continuous monitoring of {self.monitor_dir} (interval: {interval}s)")
        self.logger.info("Press Ctrl+C to stop")
        
        try:
            while True:
                processed = self.fetch_files_once()
                
                # Show stats
                stats = self.get_stats()
                if processed > 0:
                    self.logger.info(f"Stats: {stats}")
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            self.logger.info("Monitoring stopped by user")
        except Exception as e:
            self.logger.error(f"Error in continuous monitoring: {e}")
    
    def get_stats(self):
        """Get current statistics"""
        monitor_files = len(list(self.monitor_dir.glob("*"))) if self.monitor_dir.exists() else 0
        transcript_files = len(list(self.transcripts_dir.glob("*.json"))) if self.transcripts_dir.exists() else 0
        
        return {
            'total_processed': len(self.processed_files),
            'files_in_monitor': monitor_files,
            'transcript_files': transcript_files,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    
    def show_status(self):
        """Show current status"""
        print("\n=== Audio Fetcher and Processor Status ===")
        
        stats = self.get_stats()
        for key, value in stats.items():
            print(f"{key.replace('_', ' ').title()}: {value}")
        
        print(f"\nMonitor directory: {self.monitor_dir}")
        monitor_exists = "✓" if self.monitor_dir.exists() else "✗"
        print(f"  {monitor_exists} Directory exists")
        
        if self.monitor_dir.exists():
            audio_files = [f for f in self.monitor_dir.iterdir() 
                          if f.is_file() and self.is_audio_file(f)]
            print(f"  Audio files: {len(audio_files)}")
        
        print(f"\nTranscripts directory: {self.transcripts_dir}")
        transcripts_exist = "✓" if self.transcripts_dir.exists() else "✗"
        print(f"  {transcripts_exist} Directory exists")
        
        if self.transcripts_dir.exists():
            transcript_files = list(self.transcripts_dir.glob("*.json"))
            print(f"  Transcript files: {len(transcript_files)}")
        
        print(f"\nRecording Processor: {'✓ Available' if self.recording_processor else '✗ Not available'}")
        print(f"Log file: {self.log_file}")
        print(f"Supported formats: {', '.join(sorted(self.audio_formats))}")
        
        # Show recent transcripts
        if self.transcripts_dir.exists():
            transcript_files = sorted(
                [f for f in self.transcripts_dir.iterdir() if f.suffix == '.json'],
                key=lambda x: x.stat().st_mtime,
                reverse=True
            )
            
            if transcript_files:
                print(f"\nRecent transcripts (last 3):")
                for transcript_file in transcript_files[:3]:
                    try:
                        mod_time = datetime.fromtimestamp(transcript_file.stat().st_mtime)
                        print(f"  • {transcript_file.name} ({mod_time.strftime('%Y-%m-%d %H:%M:%S')})")
                    except:
                        print(f"  • {transcript_file.name}")


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Audio File Fetcher and Processor for Asterisk Recordings')
    parser.add_argument('--mode', choices=['single', 'continuous', 'status'], 
                       default='continuous', help='Operation mode')
    parser.add_argument('--interval', type=int, default=30, 
                       help='Scan interval in seconds (continuous mode)')
    
    args = parser.parse_args()
    
    # Create fetcher
    fetcher = AudioFetcher()
    
    if args.mode == 'single':
        # Single scan
        print("Running single scan...")
        count = fetcher.fetch_files_once()
        print(f"Processed {count} files")
        
    elif args.mode == 'continuous':
        # Continuous monitoring
        fetcher.run_continuous(args.interval)
        
    elif args.mode == 'status':
        # Show status
        fetcher.show_status()


if __name__ == "__main__":
    main()
