#!/usr/bin/env python3
"""
Simple batch uploader for pest data JSON files to MongoDB

Usage:
    python batch_upload_pests.py
"""

import os
import json
import sys
from pathlib import Path

# Import our database functions
from db_uploading.pest_profile_db import upsert_pest_profile, get_by_pest_key, normalize_pest_key

def main():
    """Upload all JSON files from pest_data directory"""
    
    # Path to pest data directory
    pest_data_dir = Path("pest_data")
    
    if not pest_data_dir.exists():
        print(f"❌ Directory {pest_data_dir} not found!")
        sys.exit(1)
    
    # Get all JSON files
    json_files = list(pest_data_dir.glob("*.json"))
    
    if not json_files:
        print(f"❌ No JSON files found in {pest_data_dir}")
        sys.exit(1)
    
    print(f"📂 Found {len(json_files)} JSON files")
    print("🚀 Starting upload process...\n")
    
    success_count = 0
    error_count = 0
    
    for json_file in json_files:
        try:
            print(f"📄 Processing: {json_file.name}")
            
            # Read JSON file
            with open(json_file, 'r', encoding='utf-8') as f:
                pest_data = json.load(f)
            
            # Upload to database
            upsert_pest_profile(pest_data)
            success_count += 1
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            error_count += 1
    
    # Summary
    print(f"\n{'='*50}")
    print(f"📊 Upload Summary:")
    print(f"   ✅ Successful: {success_count}")
    print(f"   ❌ Errors: {error_count}")
    print(f"   📁 Total files: {len(json_files)}")
    print(f"{'='*50}")

if __name__ == "__main__":
    main()
