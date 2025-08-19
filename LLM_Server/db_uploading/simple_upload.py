#!/usr/bin/env python3
"""
Simple soil data uploader - reads JSON files from soil_data folder and uploads to MongoDB
"""

import json
import os
from pathlib import Path
from db_uploading.soil_profile_db import upsert_soil_profile, CONNECTION_OK

def main():
    # Check connection
    if not CONNECTION_OK:
        print("❌ No database connection. Please check your MongoDB setup.")
        return
    
    # Get soil_data folder path
    soil_data_folder = Path(__file__).parent / "soil_data"
    
    if not soil_data_folder.exists():
        print(f"❌ Folder not found: {soil_data_folder}")
        return
    
    # Process all JSON files
    json_files = list(soil_data_folder.glob("*.json"))
    
    print(f"📂 Found {len(json_files)} JSON files to upload...")
    
    for json_file in json_files:
        try:
            # Load JSON data
            with open(json_file, 'r', encoding='utf-8') as f:
                soil_data = json.load(f)
            
            # Upload to database
            upsert_soil_profile(soil_data)
            
            print(f"✅ Uploaded: {soil_data.get('soil_name', json_file.stem)}")
            
        except Exception as e:
            print(f"❌ Error with {json_file.name}: {e}")
    
    print("🎉 Upload process completed!")

if __name__ == "__main__":
    main()
