#!/usr/bin/env python3
"""
Setup script for kisan_ai.pest_profiles (Part 1: DB outline only)

- Creates/updates collection with JSON Schema validation
- Creates indexes (unique on pest_key, etc.)
- Provides helper functions for later inserts/queries
"""

import os
import sys
import datetime as dt
from dotenv import load_dotenv
from pymongo import MongoClient, ASCENDING, TEXT
from pymongo.server_api import ServerApi
from pymongo.errors import CollectionInvalid
import certifi

# --------------------------------------------------------------------
# 1) Load env & connect
# --------------------------------------------------------------------
load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
DATABASE_NAME = os.getenv("DATABASE_NAME", "kisan_ai")
COLLECTION_NAME = os.getenv("PEST_COLLECTION_NAME", "pest_profiles")

if not MONGODB_URI:
    print("⚠️  Please set MONGODB_URI in your .env file.", file=sys.stderr)
    sys.exit(1)

try:
    client = MongoClient(
        MONGODB_URI,
        server_api=ServerApi("1"),
        serverSelectionTimeoutMS=20000,
        tls=True,
        tlsCAFile=certifi.where(),
    )
    client.admin.command("ping")
    print(f"🌐 Connected to MongoDB Atlas")
except Exception as e:
    print(f"❌ Connection failed: {e}")
    print("🔧 Checklist: IP allowlist, SRV URI, dnspython, VPN off, certifi CA.")
    sys.exit(1)

db = client[DATABASE_NAME]
coll = db[COLLECTION_NAME]

# --------------------------------------------------------------------
# 2) JSON Schema (validation rules) - Updated to match actual JSON structure
# --------------------------------------------------------------------
validation_schema = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["common_name", "scientific_name"],
        "properties": {
            "pest_key": { "bsonType": "string", "description": "lowercase unique slug (deprecated)" },
            "pest_id": { "bsonType": "string" },
            "common_name": { "bsonType": "string" },
            "scientific_name": { "bsonType": "string" },
            "category": { "bsonType": "string" },
            "description": { "bsonType": "string" },
            
            "identification": { 
                "bsonType": "object",
                "properties": {
                    "physical_signs": { "bsonType": ["array"], "items": { "bsonType": "string" } },
                    "visual_images": { "bsonType": ["array"], "items": { "bsonType": "string" } }
                }
            },
            
            "attack_details": {
                "bsonType": "object",
                "properties": {
                    "agriculture_stage": { "bsonType": ["array"], "items": { "bsonType": "string" } },
                    "seasons": { "bsonType": ["array"], "items": { "bsonType": "string" } },
                    "favourable_conditions": {
                        "bsonType": "object",
                        "properties": {
                            "climate": { "bsonType": "string" },
                            "soil_type": { "bsonType": ["array"], "items": { "bsonType": "string" } },
                            "soil_conditions": { "bsonType": ["array"], "items": { "bsonType": "string" } },
                            "ecological_factors": { "bsonType": ["array"], "items": { "bsonType": "string" } }
                        }
                    },
                    "geographical_distribution": { "bsonType": ["array"], "items": { "bsonType": "string" } },
                    "crops_attacked": { "bsonType": ["array"], "items": { "bsonType": "string" } }
                }
            },
            
            "impact": {
                "bsonType": "object",
                "properties": {
                    "min_crop_loss_percent": { "bsonType": ["number", "int"] },
                    "max_crop_loss_percent": { "bsonType": ["number", "int"] },
                    "economic_loss_estimate": {
                        "bsonType": "object",
                        "properties": {
                            "currency": { "bsonType": "string" },
                            "min_loss": { "bsonType": ["number", "int"] },
                            "max_loss": { "bsonType": ["number", "int"] },
                            "unit": { "bsonType": "string" }
                        }
                    }
                }
            },
            
            "management_strategies": {
                "bsonType": "object",
                "properties": {
                    "mechanical_methods": { "bsonType": ["array"], "items": { "bsonType": "string" } },
                    "cultural_methods": { "bsonType": ["array"], "items": { "bsonType": "string" } },
                    "biological_control": { 
                        "bsonType": ["array"], 
                        "items": { 
                            "bsonType": "object",
                            "properties": {
                                "agent": { "bsonType": "string" },
                                "method": { "bsonType": "string" }
                            }
                        }
                    },
                    "chemical_control": {
                        "bsonType": "object",
                        "properties": {
                            "preventive": { 
                                "bsonType": ["array"],
                                "items": {
                                    "bsonType": "object",
                                    "properties": {
                                        "pesticide_name": { "bsonType": "string" },
                                        "dosage": { "bsonType": "string" },
                                        "application_stage": { "bsonType": "string" }
                                    }
                                }
                            },
                            "curative": { 
                                "bsonType": ["array"],
                                "items": {
                                    "bsonType": "object",
                                    "properties": {
                                        "pesticide_name": { "bsonType": "string" },
                                        "dosage": { "bsonType": "string" },
                                        "application_stage": { "bsonType": "string" }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            
            "pesticides_market": {
                "bsonType": ["array"],
                "items": {
                    "bsonType": "object",
                    "properties": {
                        "brand_name": { "bsonType": "string" },
                        "active_ingredient": { "bsonType": "string" },
                        "formulation": { "bsonType": "string" },
                        "cost_per_unit": {
                            "bsonType": "object",
                            "properties": {
                                "currency": { "bsonType": "string" },
                                "amount": { "bsonType": ["number", "int"] },
                                "unit": { "bsonType": "string" }
                            }
                        }
                    }
                }
            },
            
            "references": { "bsonType": ["array"], "items": { "bsonType": "string" } },
            "last_updated": { "bsonType": ["date", "string"] },
            "updated_at": { "bsonType": ["date", "string"] },
            "version": { "bsonType": "string" }
        }
    }
}

def ensure_collection_with_validation():
    try:
        db.create_collection(
            COLLECTION_NAME,
            validator=validation_schema,
            validationLevel="moderate"
        )
        print(f"✅ Created collection '{COLLECTION_NAME}' with validation.")
    except CollectionInvalid:
        db.command({
            "collMod": COLLECTION_NAME,
            "validator": validation_schema,
            "validationLevel": "moderate"
        })
        print(f"🔧 Updated validator for existing collection '{COLLECTION_NAME}'.")

# --------------------------------------------------------------------
# 3) Indexes
# --------------------------------------------------------------------
def ensure_indexes():
    # Primary retrieval - using common_name as primary key
    coll.create_index([("common_name", ASCENDING)], unique=True, name="uniq_common_name")
    # Secondary indexes
    coll.create_index([("pest_key", ASCENDING)], name="pest_key_idx")  # Keep for backward compatibility
    coll.create_index([("pest_id", ASCENDING)], name="pest_id_idx")
    coll.create_index([("scientific_name", ASCENDING)], name="scientific_name_idx")
    coll.create_index([("category", ASCENDING)], name="category_idx")
    coll.create_index([("attack_details.crops_attacked", ASCENDING)], name="crops_attacked_idx")
    coll.create_index([("attack_details.geographical_distribution", ASCENDING)], name="geographical_distribution_idx")
    coll.create_index([("attack_details.seasons", ASCENDING)], name="seasons_idx")
    coll.create_index([("attack_details.favourable_conditions.soil_type", ASCENDING)], name="soil_type_idx")
    # Text search across key narrative fields
    coll.create_index({
        "common_name": "text",
        "scientific_name": "text",
        "description": "text",
        "identification.physical_signs": "text",
        "management_strategies.mechanical_methods": "text",
        "management_strategies.cultural_methods": "text"
    }, name="text_pest_search")
    print("✅ Indexes ensured.")

# --------------------------------------------------------------------
# 4) Helpers
# --------------------------------------------------------------------
def normalize_pest_key(k: str) -> str:
    """Convert pest name to normalized key (lowercase, hyphenated)"""
    return "-".join(k.strip().lower().split())

def transform_json_to_schema(json_data: dict) -> dict:
    """Transform JSON data to match our schema structure"""
    # Generate pest_key from common_name for backward compatibility if not provided
    if "pest_key" not in json_data:
        json_data["pest_key"] = normalize_pest_key(json_data.get("common_name", ""))
    else:
        json_data["pest_key"] = normalize_pest_key(json_data["pest_key"])
    
    # Convert last_updated to updated_at if present
    if "last_updated" in json_data and "updated_at" not in json_data:
        json_data["updated_at"] = json_data["last_updated"]
    
    # Ensure updated_at is set
    json_data["updated_at"] = dt.datetime.utcnow()
    json_data.setdefault("version", "v1")
    
    return json_data

def upsert_pest_profile(doc: dict):
    """Upsert one pest profile document using common_name as primary key."""
    if "common_name" not in doc:
        raise ValueError("common_name is required")
    
    # Transform the document to match our schema
    doc = transform_json_to_schema(doc)
    
    # Use common_name as the primary key for upsert
    res = coll.update_one({"common_name": doc["common_name"]}, {"$set": doc}, upsert=True)
    print(("➕ Inserted " if res.upserted_id else "♻️  Updated ") + doc["common_name"])
    return res

def get_by_pest_key(pest_key: str):
    """Get pest profile by pest_key (for backward compatibility)"""
    return coll.find_one({"pest_key": normalize_pest_key(pest_key)})

def get_by_common_name(common_name: str):
    """Get pest profile by common name (primary lookup method)"""
    return coll.find_one({"common_name": common_name})

# --------------------------------------------------------------------
# 5) Run
# --------------------------------------------------------------------
if __name__ == "__main__":
    ensure_collection_with_validation()
    ensure_indexes()
    print(f"✅ Setup complete for {DATABASE_NAME}.{COLLECTION_NAME}")

    # --- Optional sanity test (leave commented) ---
    """
    sample = {
        "common_name": "Brown Planthopper",
        "scientific_name": "Nilaparvata lugens",
        "category": "Insect",
        "description": "A major rice pest that causes hopper burn and transmits viruses.",
        "attack_details": {
            "seasons": ["Kharif", "Rabi"],
            "crops_attacked": ["Rice"],
            "geographical_distribution": ["West Bengal", "Tamil Nadu"],
            "favourable_conditions": {
                "soil_type": ["Clay loam", "Silty soils"]
            }
        }
    }
    upsert_pest_profile(sample)
    print(get_by_common_name("Brown Planthopper"))
    """
