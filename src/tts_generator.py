#!/usr/bin/env python3
"""
Text-to-Speech Generator using Google Cloud APIs
Simple utility to generate multilingual audio from text.
"""

import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import our main processor
from recording_processor import RecordingProcessorGoogle

def main():
    """Main function for TTS generation"""
    parser = argparse.ArgumentParser(description='Generate speech from text using Google Cloud TTS')
    parser.add_argument('--text', type=str, help='Text to convert to speech')
    parser.add_argument('--language', type=str, default='en', help='Target language code (default: en)')
    parser.add_argument('--list-languages', action='store_true', help='List supported languages')
    parser.add_argument('--interactive', action='store_true', help='Interactive mode')
    
    args = parser.parse_args()
    
    try:
        processor = RecordingProcessorGoogle()
        
        if args.list_languages:
            list_supported_languages(processor)
            return
        
        if args.interactive or (not args.text and not args.list_languages):
            interactive_mode(processor)
            return
        
        if args.text:
            generate_speech(processor, args.text, args.language)
            return
            
        parser.print_help()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

def list_supported_languages(processor):
    """List supported languages"""
    print("🎯 Supported Languages for TTS")
    print("=" * 40)
    
    languages = {
        "en": "English",
        "hi": "Hindi", 
        "bn": "Bengali",
        "te": "Telugu",
        "mr": "Marathi", 
        "ta": "Tamil",
        "gu": "Gujarati",
        "ur": "Urdu",
        "kn": "Kannada",
        "ml": "Malayalam",
        "pa": "Punjabi",
        "es": "Spanish",
        "fr": "French", 
        "de": "German",
        "it": "Italian",
        "pt": "Portuguese",
        "ru": "Russian",
        "ja": "Japanese",
        "ko": "Korean",
        "zh": "Chinese",
        "ar": "Arabic"
    }
    
    for code, name in languages.items():
        print(f"  {code} - {name}")

def interactive_mode(processor):
    """Interactive TTS generation"""
    print("🎤 Interactive Text-to-Speech Generator")
    print("=" * 40)
    print("Type 'quit' to exit, 'languages' to list supported languages")
    print()
    
    while True:
        try:
            text = input("Enter text to convert: ").strip()
            
            if text.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break
                
            if text.lower() == 'languages':
                list_supported_languages(processor)
                continue
                
            if not text:
                continue
                
            language = input("Enter language code (default: en): ").strip() or 'en'
            
            generate_speech(processor, text, language)
            print()
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

def generate_speech(processor, text, language):
    """Generate speech from text"""
    print(f"🔊 Generating speech in {language}...")
    
    try:
        result = processor.generate_multilingual_audio(text, language)
        
        if result['success']:
            print(f"✅ Audio generated successfully!")
            print(f"📁 File: {result['audio_file']}")
            print(f"🌍 Language: {result['target_language']}")
            if result.get('translated_text') != text:
                print(f"📝 Translated text: {result['translated_text']}")
        else:
            print(f"❌ Failed to generate audio: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Error generating speech: {e}")

if __name__ == "__main__":
    main()
