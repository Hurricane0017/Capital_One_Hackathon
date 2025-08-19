#!/usr/bin/env python3
"""
Upload script for scheme profiles from JSON files to MongoDB

This script reads all JSON files from the schemes_data directory and uploads them
to the scheme_profiles collection in MongoDB, using the structure defined in scheme_profile_db.py
"""

import os
import sys
import json
import datetime as dt
from pathlib import Path
from dotenv import load_dotenv

# Import our database setup and helper functions
from scheme_profile_db import (
    client, db, coll, 
    upsert_scheme_profile, 
    get_by_scheme_name,
    get_by_scheme_id,
    normalize_scheme_key,
    search_schemes_by_type,
    search_schemes_by_crop,
    search_schemes_by_farmer_segment,
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

def process_schemes_data_directory(schemes_data_dir: str = "schemes_data"):
    """Process all JSON files in the schemes_data directory"""
    
    # Get the absolute path to the schemes_data directory
    script_dir = Path(__file__).parent
    schemes_data_path = script_dir / schemes_data_dir
    
    if not schemes_data_path.exists():
        print(f"❌ Directory {schemes_data_path} does not exist")
        return
    
    # Find all JSON files
    json_files = list(schemes_data_path.glob("*.json"))
    
    if not json_files:
        print(f"❌ No JSON files found in {schemes_data_path}")
        return
    
    print(f"📂 Found {len(json_files)} JSON files in {schemes_data_path}")
    
    # Process each file
    successful_uploads = 0
    failed_uploads = 0
    
    for json_file in json_files:
        print(f"\n📄 Processing: {json_file.name}")
        
        # Load the JSON data
        scheme_data = load_json_file(json_file)
        if scheme_data is None:
            failed_uploads += 1
            continue
        
        try:
            # Upload to MongoDB
            upsert_scheme_profile(scheme_data)
            successful_uploads += 1
            
            # Verify the upload
            scheme_name = scheme_data.get("name", "")
            uploaded_doc = get_by_scheme_name(scheme_name)
            if uploaded_doc:
                print(f"   ✅ Verified: {uploaded_doc['name']} (ID: {uploaded_doc.get('scheme_id', 'N/A')})")
            else:
                print(f"   ⚠️  Upload completed but verification failed for {scheme_name}")
                
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
        print(f"\n🎉 Successfully uploaded {successful_uploads} scheme profiles to {DATABASE_NAME}.{COLLECTION_NAME}")

def list_uploaded_schemes():
    """List all schemes currently in the database"""
    try:
        count = coll.count_documents({})
        print(f"\n📊 Database currently contains {count} scheme profiles:")
        
        if count > 0:
            schemes = coll.find({}, {"name": 1, "scheme_id": 1, "type": 1, "agency.name": 1}).sort("name", 1)
            for i, scheme in enumerate(schemes, 1):
                agency_name = scheme.get('agency', {}).get('name', 'N/A')
                print(f"   {i:2d}. {scheme['name']} (ID: {scheme.get('scheme_id', 'N/A')}) - Type: {scheme.get('type', 'N/A')} - Agency: {agency_name}")
    except Exception as e:
        print(f"❌ Error listing schemes: {e}")

def search_scheme_by_name(search_term: str):
    """Search for a scheme by name"""
    try:
        # Search in scheme name and scheme_id
        query = {
            "$or": [
                {"name": {"$regex": search_term, "$options": "i"}},
                {"scheme_id": {"$regex": search_term, "$options": "i"}}
            ]
        }
        
        results = list(coll.find(query, {"name": 1, "scheme_id": 1, "type": 1, "agency.name": 1}))
        
        if results:
            print(f"\n🔍 Found {len(results)} scheme(s) matching '{search_term}':")
            for scheme in results:
                agency_name = scheme.get('agency', {}).get('name', 'N/A')
                print(f"   • {scheme['name']} (ID: {scheme.get('scheme_id', 'N/A')}) - Type: {scheme.get('type', 'N/A')} - Agency: {agency_name}")
        else:
            print(f"❌ No schemes found matching '{search_term}'")
            
    except Exception as e:
        print(f"❌ Error searching: {e}")

def list_schemes_by_type():
    """List schemes grouped by type"""
    try:
        pipeline = [
            {"$group": {"_id": "$type", "count": {"$sum": 1}, "schemes": {"$push": {"name": "$name", "scheme_id": "$scheme_id"}}}},
            {"$sort": {"_id": 1}}
        ]
        
        results = list(coll.aggregate(pipeline))
        
        if results:
            print(f"\n📊 Schemes by Type:")
            for result in results:
                scheme_type = result['_id'] or 'Unknown'
                count = result['count']
                print(f"\n   {scheme_type.upper()} ({count} schemes):")
                for scheme in result['schemes'][:5]:  # Show first 5 schemes
                    print(f"     • {scheme['name']} (ID: {scheme.get('scheme_id', 'N/A')})")
                if len(result['schemes']) > 5:
                    print(f"     ... and {len(result['schemes']) - 5} more")
        else:
            print(f"❌ No schemes found")
            
    except Exception as e:
        print(f"❌ Error listing schemes by type: {e}")

def list_schemes_by_farmer_segment():
    """List schemes by farmer segment"""
    try:
        pipeline = [
            {"$unwind": "$eligibility.farmer_segments"},
            {"$group": {"_id": "$eligibility.farmer_segments", "count": {"$sum": 1}, "schemes": {"$addToSet": {"name": "$name", "scheme_id": "$scheme_id"}}}},
            {"$sort": {"_id": 1}}
        ]
        
        results = list(coll.aggregate(pipeline))
        
        if results:
            print(f"\n🎯 Schemes by Farmer Segment:")
            for result in results:
                segment = result['_id']
                count = result['count']
                print(f"\n   {segment.upper().replace('_', ' ')} ({count} schemes):")
                for scheme in result['schemes'][:3]:  # Show first 3 schemes
                    print(f"     • {scheme['name']} (ID: {scheme.get('scheme_id', 'N/A')})")
                if len(result['schemes']) > 3:
                    print(f"     ... and {len(result['schemes']) - 3} more")
        else:
            print(f"❌ No schemes found")
            
    except Exception as e:
        print(f"❌ Error listing schemes by farmer segment: {e}")

def main():
    """Main function with command line interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Upload scheme data from JSON files to MongoDB")
    parser.add_argument("--upload", action="store_true", help="Upload all JSON files from schemes_data directory")
    parser.add_argument("--list", action="store_true", help="List all uploaded schemes")
    parser.add_argument("--search", type=str, help="Search for a scheme by name or ID")
    parser.add_argument("--by-type", action="store_true", help="List schemes grouped by type")
    parser.add_argument("--by-segment", action="store_true", help="List schemes by farmer segment")
    parser.add_argument("--dir", type=str, default="schemes_data", help="Directory containing JSON files (default: schemes_data)")
    
    args = parser.parse_args()
    
    # Test database connection
    try:
        client.admin.command("ping")
        print(f"🌐 Connected to MongoDB: {DATABASE_NAME}.{COLLECTION_NAME}")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        sys.exit(1)
    
    if args.upload:
        process_schemes_data_directory(args.dir)
    elif args.list:
        list_uploaded_schemes()
    elif args.search:
        search_scheme_by_name(args.search)
    elif args.by_type:
        list_schemes_by_type()
    elif args.by_segment:
        list_schemes_by_farmer_segment()
    else:
        # Default behavior: show help and list current schemes
        parser.print_help()
        print()
        list_uploaded_schemes()

if __name__ == "__main__":
    main()
