#!/usr/bin/env python3
"""
Upload script for soil data from JSON files to MongoDB
Reads all JSON files from the soil_data folder and uploads them to the soil_profiles collection
"""

import json
import os
import sys
from pathlib import Path

# Import the setup and helper functions from soil_profile_db.py
from db_uploading.soil_profile_db import upsert_soil_profile, get_by_soil_key, CONNECTION_OK

def load_json_files(data_folder_path):
    """
    Load all JSON files from the specified folder
    Returns a list of dictionaries containing soil profile data
    """
    soil_profiles = []
    data_folder = Path(data_folder_path)
    
    if not data_folder.exists():
        print(f"❌ Data folder not found: {data_folder_path}")
        return soil_profiles
    
    json_files = list(data_folder.glob("*.json"))
    
    if not json_files:
        print(f"⚠️  No JSON files found in {data_folder_path}")
        return soil_profiles
    
    print(f"📂 Found {len(json_files)} JSON files to process:")
    
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                soil_profiles.append(data)
                print(f"   ✅ Loaded: {json_file.name}")
        except json.JSONDecodeError as e:
            print(f"   ❌ Invalid JSON in {json_file.name}: {e}")
        except Exception as e:
            print(f"   ❌ Error loading {json_file.name}: {e}")
    
    return soil_profiles

def upload_soil_profiles(soil_profiles):
    """
    Upload soil profiles to MongoDB using the upsert_soil_profile function
    """
    if not CONNECTION_OK:
        print("❌ Cannot upload data - no database connection")
        return
    
    if not soil_profiles:
        print("⚠️  No soil profiles to upload")
        return
    
    print(f"\n🚀 Starting upload of {len(soil_profiles)} soil profiles...")
    
    success_count = 0
    error_count = 0
    
    for profile in soil_profiles:
        try:
            # Validate that required fields exist
            if 'soil_key' not in profile:
                print(f"   ❌ Missing soil_key in profile: {profile.get('soil_name', 'Unknown')}")
                error_count += 1
                continue
            
            if 'soil_name' not in profile:
                print(f"   ❌ Missing soil_name in profile: {profile['soil_key']}")
                error_count += 1
                continue
            
            # Upload the profile
            upsert_soil_profile(profile)
            success_count += 1
            
        except Exception as e:
            print(f"   ❌ Error uploading {profile.get('soil_key', 'Unknown')}: {e}")
            error_count += 1
    
    print(f"\n📊 Upload Summary:")
    print(f"   ✅ Successfully uploaded: {success_count}")
    print(f"   ❌ Errors: {error_count}")
    
    return success_count, error_count

def verify_uploads(soil_profiles):
    """
    Verify that uploaded profiles can be retrieved from the database
    """
    if not CONNECTION_OK:
        print("❌ Cannot verify uploads - no database connection")
        return
    
    print(f"\n🔍 Verifying uploaded data...")
    
    verified_count = 0
    not_found_count = 0
    
    for profile in soil_profiles:
        soil_key = profile.get('soil_key')
        if not soil_key:
            continue
        
        try:
            retrieved = get_by_soil_key(soil_key)
            if retrieved:
                print(f"   ✅ Verified: {soil_key} - {retrieved['soil_name']}")
                verified_count += 1
            else:
                print(f"   ❌ Not found: {soil_key}")
                not_found_count += 1
        except Exception as e:
            print(f"   ❌ Error verifying {soil_key}: {e}")
            not_found_count += 1
    
    print(f"\n📋 Verification Summary:")
    print(f"   ✅ Verified in database: {verified_count}")
    print(f"   ❌ Not found: {not_found_count}")

def main():
    """Main function to orchestrate the upload process"""
    print("🌱 Soil Data Upload Script")
    print("=" * 50)
    
    # Check database connection first
    if not CONNECTION_OK:
        print("❌ No database connection available. Please check your MongoDB setup.")
        sys.exit(1)
    
    # Define the path to the soil_data folder
    current_dir = Path(__file__).parent
    soil_data_folder = current_dir / "soil_data"
    
    # Load JSON files
    print(f"📁 Loading JSON files from: {soil_data_folder}")
    soil_profiles = load_json_files(soil_data_folder)
    
    if not soil_profiles:
        print("❌ No valid soil profiles loaded. Exiting.")
        sys.exit(1)
    
    # Upload to database
    success_count, error_count = upload_soil_profiles(soil_profiles)
    
    if success_count > 0:
        # Verify uploads
        verify_uploads(soil_profiles)
        print(f"\n🎉 Upload process completed! {success_count} profiles uploaded successfully.")
    else:
        print(f"\n❌ Upload failed. No profiles were uploaded.")
        sys.exit(1)

if __name__ == "__main__":
    main()
