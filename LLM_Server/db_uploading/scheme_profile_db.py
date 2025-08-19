#!/usr/bin/env python3
"""
Setup script for kisan_ai.scheme_profiles

- Creates/updates collection with JSON Schema validation
- Creates indexes (unique on scheme name, etc.)
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
COLLECTION_NAME = os.getenv("SCHEME_COLLECTION_NAME", "scheme_profiles")

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
# 2) JSON Schema (validation rules) - Based on provided scheme structure
# --------------------------------------------------------------------
validation_schema = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["name", "scheme_id"],
        "properties": {
            "scheme_id": { "bsonType": "string", "description": "Unique scheme identifier" },
            "name": { "bsonType": "string", "description": "Scheme name - primary key" },
            "type": { "bsonType": "string" },
            
            "agency": {
                "bsonType": "object",
                "properties": {
                    "name": { "bsonType": "string" },
                    "type": { "bsonType": "string" },
                    "contact": {
                        "bsonType": "object",
                        "properties": {
                            "helpline": { "bsonType": ["string", "null"] },
                            "email": { "bsonType": ["string", "null"] },
                            "website": { "bsonType": ["string", "null"] }
                        }
                    }
                }
            },
            
            "validity": {
                "bsonType": "object",
                "properties": {
                    "start_date": { "bsonType": ["string", "date", "null"] },
                    "end_date": { "bsonType": ["string", "date", "null"] },
                    "application_windows": {
                        "bsonType": "array",
                        "items": {
                            "bsonType": "object",
                            "properties": {
                                "from": { "bsonType": ["string", "date"] },
                                "to": { "bsonType": ["string", "date"] },
                                "season": { "bsonType": "string" }
                            }
                        }
                    }
                }
            },
            
            "eligibility": {
                "bsonType": "object",
                "properties": {
                    "farmer_segments": { "bsonType": "array", "items": { "bsonType": "string" } },
                    "income_categories": { "bsonType": "array", "items": { "bsonType": "string" } },
                    "income_cap_inr_per_year": { "bsonType": ["number", "int", "null"] },
                    "caste_categories": { "bsonType": "array", "items": { "bsonType": "string" } },
                    "special_status": { "bsonType": "array", "items": { "bsonType": "string" } },
                    "age_min": { "bsonType": ["number", "int", "null"] },
                    "age_max": { "bsonType": ["number", "int", "null"] },
                    "land_holding_max_ha": { "bsonType": ["number", "null"] },
                    "other_conditions": { "bsonType": "array", "items": { "bsonType": "string" } }
                }
            },
            
            "benefits": {
                "bsonType": "array",
                "items": {
                    "bsonType": "object",
                    "properties": {
                        "benefit_type": { "bsonType": "string" },
                        "description": { "bsonType": "string" },
                        "financials": {
                            "bsonType": "object",
                            "properties": {
                                "sum_insured_inr": { "bsonType": ["number", "int", "null"] },
                                "premium_inr": { "bsonType": ["number", "int", "null"] },
                                "premium_rate_percent": { "bsonType": ["number", "null"] },
                                "cost_distribution": {
                                    "bsonType": "object",
                                    "properties": {
                                        "govt_percent": { "bsonType": ["number", "int"] },
                                        "beneficiary_percent": { "bsonType": ["number", "int"] },
                                        "other_sources_percent": { "bsonType": ["number", "int"] }
                                    }
                                },
                                "subsidy_percent": { "bsonType": ["number", "null"] },
                                "cash_transfer_amount_inr": { "bsonType": ["number", "int", "null"] }
                            }
                        },
                        "coverage": {
                            "bsonType": "object",
                            "properties": {
                                "crops": { "bsonType": "array", "items": { "bsonType": "string" } },
                                "seasons": { "bsonType": "array", "items": { "bsonType": "string" } },
                                "perils_covered": { "bsonType": "array", "items": { "bsonType": "string" } },
                                "stages_covered": { "bsonType": "array", "items": { "bsonType": "string" } }
                            }
                        },
                        "conditions": { "bsonType": "array", "items": { "bsonType": "string" } }
                    }
                }
            },
            
            "application": {
                "bsonType": "object",
                "properties": {
                    "mode": { "bsonType": "array", "items": { "bsonType": "string" } },
                    "portal_urls": { "bsonType": "array", "items": { "bsonType": "string" } },
                    "documents_required": { "bsonType": "array", "items": { "bsonType": "string" } },
                    "fees_inr": { "bsonType": ["number", "int"] }
                }
            },
            
            "disbursal": {
                "bsonType": "object",
                "properties": {
                    "mode": { "bsonType": "string" },
                    "timeline_days": { "bsonType": ["number", "int"] }
                }
            },
            
            "budget": {
                "bsonType": "object",
                "properties": {
                    "fy_allocation_inr": { "bsonType": ["number", "int", "null"] },
                    "beneficiaries_target": { "bsonType": ["number", "int", "null"] },
                    "beneficiaries_actual": { "bsonType": ["number", "int", "null"] }
                }
            },
            
            "faqs": {
                "bsonType": "array",
                "items": {
                    "bsonType": "object",
                    "properties": {
                        "q": { "bsonType": "string" },
                        "a": { "bsonType": "string" }
                    }
                }
            },
            
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
    # Primary retrieval - using scheme name as primary key
    coll.create_index([("name", ASCENDING)], unique=True, name="uniq_scheme_name")
    # Secondary indexes
    coll.create_index([("scheme_id", ASCENDING)], unique=True, name="uniq_scheme_id")
    coll.create_index([("type", ASCENDING)], name="scheme_type_idx")
    coll.create_index([("agency.name", ASCENDING)], name="agency_name_idx")
    coll.create_index([("agency.type", ASCENDING)], name="agency_type_idx")
    coll.create_index([("eligibility.farmer_segments", ASCENDING)], name="farmer_segments_idx")
    coll.create_index([("eligibility.caste_categories", ASCENDING)], name="caste_categories_idx")
    coll.create_index([("benefits.benefit_type", ASCENDING)], name="benefit_type_idx")
    coll.create_index([("benefits.coverage.crops", ASCENDING)], name="crops_covered_idx")
    coll.create_index([("benefits.coverage.seasons", ASCENDING)], name="seasons_covered_idx")
    coll.create_index([("validity.start_date", ASCENDING)], name="start_date_idx")
    coll.create_index([("validity.end_date", ASCENDING)], name="end_date_idx")
    
    # Text search across key narrative fields
    coll.create_index({
        "name": "text",
        "scheme_id": "text",
        "benefits.description": "text",
        "eligibility.other_conditions": "text",
        "faqs.q": "text",
        "faqs.a": "text"
    }, name="text_scheme_search")
    print("✅ Indexes ensured.")

# --------------------------------------------------------------------
# 4) Helpers
# --------------------------------------------------------------------
def normalize_scheme_key(k: str) -> str:
    """Convert scheme name to normalized key (lowercase, hyphenated)"""
    return "-".join(k.strip().lower().split())

def transform_json_to_schema(json_data: dict) -> dict:
    """Transform JSON data to match our schema structure"""
    # Convert last_updated to updated_at if present
    if "last_updated" in json_data and "updated_at" not in json_data:
        json_data["updated_at"] = json_data["last_updated"]
    
    # Ensure updated_at is set
    json_data["updated_at"] = dt.datetime.utcnow()
    json_data.setdefault("version", "v1")
    
    return json_data

def upsert_scheme_profile(doc: dict):
    """Upsert one scheme profile document using name as primary key."""
    if "name" not in doc:
        raise ValueError("scheme name is required")
    
    # Transform the document to match our schema
    doc = transform_json_to_schema(doc)
    
    # Use name as the primary key for upsert
    res = coll.update_one({"name": doc["name"]}, {"$set": doc}, upsert=True)
    print(("➕ Inserted " if res.upserted_id else "♻️  Updated ") + doc["name"])
    return res

def get_by_scheme_id(scheme_id: str):
    """Get scheme profile by scheme_id"""
    return coll.find_one({"scheme_id": scheme_id})

def get_by_scheme_name(name: str):
    """Get scheme profile by name (primary lookup method)"""
    return coll.find_one({"name": name})

def search_schemes_by_type(scheme_type: str):
    """Get schemes by type"""
    return list(coll.find({"type": scheme_type}))

def search_schemes_by_crop(crop: str):
    """Get schemes that cover a specific crop"""
    return list(coll.find({"benefits.coverage.crops": {"$regex": crop, "$options": "i"}}))

def search_schemes_by_farmer_segment(segment: str):
    """Get schemes for a specific farmer segment"""
    return list(coll.find({"eligibility.farmer_segments": segment}))

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
        "scheme_id": "TEST-001",
        "name": "Test Scheme",
        "type": "subsidy",
        "agency": {
            "name": "Department of Agriculture",
            "type": "government"
        },
        "eligibility": {
            "farmer_segments": ["small_and_marginal"],
            "caste_categories": ["General"]
        },
        "benefits": [{
            "benefit_type": "subsidy",
            "description": "Test subsidy scheme",
            "coverage": {
                "crops": ["Rice", "Wheat"],
                "seasons": ["Kharif", "Rabi"]
            }
        }]
    }
    upsert_scheme_profile(sample)
    print(get_by_scheme_name("Test Scheme"))
    """
