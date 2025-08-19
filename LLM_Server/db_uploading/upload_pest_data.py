#!/usr/bin/env python3
"""
Upload script for pest profiles from JSON files to MongoDB

This script reads all JSON files from the pest_data directory and uploads them
to the pest_profiles collection in MongoDB, using the structure defined in pest_profile_db.py
"""

import os
import sys
import json
import datetime as dt
from pathlib import Path
from dotenv import load_dotenv

# Import our database setup and helper functions
from db_uploading.pest_profile_db import (
    client, db, coll, 
    upsert_pest_profile, 
    get_by_common_name,
    normalize_pest_key,
    DATABASE_NAME,
    COLLECTION_NAME
)

def load_json_file(file_path: str) -> dict:
    """Load and parse a JSON file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Error loading {file_path}: {e}")
        return None

def process_pest_data_directory(pest_data_dir: str = "pest_data"):
    """Process all JSON files in the pest_data directory"""
    
    # Get the absolute path to the pest_data directory
    script_dir = Path(__file__).parent
    pest_data_path = script_dir / pest_data_dir
    
    if not pest_data_path.exists():
        print(f"❌ Directory {pest_data_path} does not exist")
        return
    
    # Find all JSON files
    json_files = list(pest_data_path.glob("*.json"))
    
    if not json_files:
        print(f"❌ No JSON files found in {pest_data_path}")
        return
    
    print(f"📂 Found {len(json_files)} JSON files in {pest_data_path}")
    
    # Process each file
    successful_uploads = 0
    failed_uploads = 0
    
    for json_file in json_files:
        print(f"\n📄 Processing: {json_file.name}")
        
        # Load the JSON data
        pest_data = load_json_file(json_file)
        if pest_data is None:
            failed_uploads += 1
            continue
        
        try:
            # Upload to MongoDB
            upsert_pest_profile(pest_data)
            successful_uploads += 1
            
            # Verify the upload
            common_name = pest_data.get("common_name", "")
            uploaded_doc = get_by_common_name(common_name)
            if uploaded_doc:
                print(f"   ✅ Verified: {uploaded_doc['common_name']} ({uploaded_doc['scientific_name']})")
            else:
                print(f"   ⚠️  Upload completed but verification failed for {common_name}")
                
        except Exception as e:
            print(f"   ❌ Failed to upload: {e}")
            failed_uploads += 1
    
    # Summary
    print(f"\n{'='*50}")
    print(f"📊 UPLOAD SUMMARY")
    print(f"{'='*50}")
    print(f"✅ Successful uploads: {successful_uploads}")
    print(f"❌ Failed uploads: {failed_uploads}")
    print(f"📁 Total files processed: {len(json_files)}")
    
    if successful_uploads > 0:
        print(f"\n🎉 Successfully uploaded {successful_uploads} pest profiles to {DATABASE_NAME}.{COLLECTION_NAME}")

def list_uploaded_pests():
    """List all pests currently in the database"""
    try:
        count = coll.count_documents({})
        print(f"\n📊 Database currently contains {count} pest profiles:")
        
        if count > 0:
            pests = coll.find({}, {"common_name": 1, "scientific_name": 1}).sort("common_name", 1)
            for i, pest in enumerate(pests, 1):
                pest_key = pest.get('pest_key', normalize_pest_key(pest['common_name']))
                print(f"   {i:2d}. {pest['common_name']} ({pest['scientific_name']}) - Key: {pest_key}")
    except Exception as e:
        print(f"❌ Error listing pests: {e}")

def search_pest_by_name(search_term: str):
    """Search for a pest by name"""
    try:
        # Search in common name and scientific name
        query = {
            "$or": [
                {"common_name": {"$regex": search_term, "$options": "i"}},
                {"scientific_name": {"$regex": search_term, "$options": "i"}}
            ]
        }
        
        results = list(coll.find(query, {"common_name": 1, "scientific_name": 1}))
        
        if results:
            print(f"\n🔍 Found {len(results)} pest(s) matching '{search_term}':")
            for pest in results:
                pest_key = pest.get('pest_key', normalize_pest_key(pest['common_name']))
                print(f"   • {pest['common_name']} ({pest['scientific_name']}) - Key: {pest_key}")
        else:
            print(f"❌ No pests found matching '{search_term}'")
            
    except Exception as e:
        print(f"❌ Error searching: {e}")

def main():
    """Main function with command line interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Upload pest data from JSON files to MongoDB")
    parser.add_argument("--upload", action="store_true", help="Upload all JSON files from pest_data directory")
    parser.add_argument("--list", action="store_true", help="List all uploaded pests")
    parser.add_argument("--search", type=str, help="Search for a pest by name")
    parser.add_argument("--dir", type=str, default="pest_data", help="Directory containing JSON files (default: pest_data)")
    
    args = parser.parse_args()
    
    # Test database connection
    try:
        client.admin.command("ping")
        print(f"🌐 Connected to MongoDB: {DATABASE_NAME}.{COLLECTION_NAME}")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        sys.exit(1)
    
    if args.upload:
        process_pest_data_directory(args.dir)
    elif args.list:
        list_uploaded_pests()
    elif args.search:
        search_pest_by_name(args.search)
    else:
        # Default behavior: show help and list current pests
        parser.print_help()
        print()
        list_uploaded_pests()

if __name__ == "__main__":
    main()
