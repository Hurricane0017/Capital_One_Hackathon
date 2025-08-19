#!/usr/bin/env python3
"""
Setup script for kisan_ai.soil_profiles (Part 1: DB outline only)

- Creates/updates collection with JSON Schema validation
- Creates indexes (unique on soil_key, etc.)
- Provides helper functions for later inserts/queries (Part 2 will use web sources)
"""

import os
import sys
import datetime as dt
from dotenv import load_dotenv
from pymongo import MongoClient, ASCENDING, TEXT
from pymongo.server_api import ServerApi
from pymongo.errors import CollectionInvalid

# Load environment variables
load_dotenv()

# --------------------------------------------------------------------
# 1) Connection
# --------------------------------------------------------------------
MONGODB_URI = os.getenv("MONGODB_URI")
DATABASE_NAME = os.getenv("DATABASE_NAME", "kisan_ai")
COLLECTION_NAME = os.getenv("SOIL_COLLECTION_NAME", "soil_profiles")

if not MONGODB_URI:
    print("⚠️  Please set MONGODB_URI in your .env file.", file=sys.stderr)
    sys.exit(1)

# Create client with ServerApi (compatible with mongodb.py setup)
# Add better error handling for connection issues
import ssl
import certifi

try:
    client = MongoClient(
        MONGODB_URI, 
        server_api=ServerApi('1'), 
        serverSelectionTimeoutMS=15000,
        tls=True,
        tlsAllowInvalidCertificates=True
    )
    db = client[DATABASE_NAME]
    COLL_NAME = COLLECTION_NAME
    coll = db[COLL_NAME]
    
    # Test connection immediately
    client.admin.command("ping")
    CONNECTION_OK = True
    print(f"🌐 Successfully connected to MongoDB Atlas (Database: {DATABASE_NAME})")
    
except Exception as e:
    print(f"⚠️  MongoDB connection failed: {e}")
    print("📝 Note: Collection operations will be skipped, but the script structure is ready.")
    CONNECTION_OK = False
    client = None
    db = None
    coll = None

# --------------------------------------------------------------------
# 2) JSON Schema (validation rules)
#    NOTE: includes `hazards` as requested.
# --------------------------------------------------------------------
validation_schema = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["soil_key", "soil_name"],
        "properties": {
            "soil_key": {
                "bsonType": "string",
                "description": "Lowercase, URL-safe unique key for retrieval"
            },
            "soil_name": {"bsonType": "string"},
            "aliases": {"bsonType": ["array"], "items": {"bsonType": "string"}},
            "color": {"bsonType": ["array"], "items": {"bsonType": "string"}},
            "texture": {"bsonType": "string"},
            "structure": {"bsonType": "string"},
            "physical_properties": {
                "bsonType": "object",
                "properties": {
                    "bulk_density_g_cm3": {"bsonType": ["double", "int", "long"]},
                    "infiltration_rate_mm_hr": {"bsonType": ["double", "int", "long"]},
                    "erosion_risk": {"bsonType": "string"}
                }
            },
            "chemical_properties": {
                "bsonType": "object",
                "properties": {
                    "pH": {
                        "bsonType": "object",
                        "properties": {
                            "min": {"bsonType": ["double", "int", "long"]},
                            "max": {"bsonType": ["double", "int", "long"]}
                        }
                    },
                    "cation_exchange_capacity_cmolkg": {
                        "bsonType": "object",
                        "properties": {
                            "min": {"bsonType": ["double", "int", "long"]},
                            "max": {"bsonType": ["double", "int", "long"]}
                        }
                    },
                    "organic_matter_pct": {
                        "bsonType": "object",
                        "properties": {
                            "min": {"bsonType": ["double", "int", "long"]},
                            "max": {"bsonType": ["double", "int", "long"]}
                        }
                    },
                    "salinity_dS_m": {
                        "bsonType": "object",
                        "properties": {
                            "max": {"bsonType": ["double", "int", "long"]}
                        }
                    },
                    "sodicity_ESP": {
                        "bsonType": "object",
                        "properties": {
                            "max": {"bsonType": ["double", "int", "long"]}
                        }
                    },
                    "free_CaCO3_pct": {
                        "bsonType": "object",
                        "properties": {
                            "min": {"bsonType": ["double", "int", "long"]},
                            "max": {"bsonType": ["double", "int", "long"]}
                        }
                    }
                }
            },
            "water_holding_capacity_pct": {
                "bsonType": ["double", "int", "long", "object"],  # allow scalar or {min,max}
            },
            "nutrients_rich_in": {"bsonType": ["array"], "items": {"bsonType": "string"}},
            "nutrients_deficient_in": {"bsonType": ["array"], "items": {"bsonType": "string"}},
            "favoured_crops": {"bsonType": ["array"], "items": {"bsonType": "string"}},
            "favoured_seasons": {"bsonType": ["array"], "items": {"bsonType": "string"}},
            "drainage": {"bsonType": "string"},
            "typical_depth_cm": {
                "bsonType": ["double", "int", "long", "object"]  # allow scalar or {min,max}
            },
            "regions": {
                "bsonType": ["array"],
                "items": {
                    "bsonType": "object",
                    "properties": {
                        "state": {"bsonType": "string"},
                        "district": {"bsonType": "string"},
                        "notes": {"bsonType": "string"}
                    }
                }
            },
            "hazards": {  # <-- added
                "bsonType": ["array"],
                "items": {"bsonType": "string"},
                "description": "e.g., waterlogging, salinity, crusting, erosion"
            },
            "notes": {"bsonType": "string"},
            "sources": {"bsonType": ["array"], "items": {"bsonType": "string"}},
            "updated_at": {"bsonType": ["date", "string"]},
            "version": {"bsonType": "string"}
        }
    }
}

def ensure_collection_with_validation():
    """Create the collection with validation, or update validator if it exists."""
    if not CONNECTION_OK:
        print("❌ Cannot create collection - no database connection")
        return
        
    try:
        db.create_collection(
            COLL_NAME,
            validator=validation_schema,
            validationLevel="moderate",  # 'strict' blocks more writes; 'moderate' is friendlier at start
        )
        print(f"✅ Created collection '{COLL_NAME}' with validation.")
    except CollectionInvalid:
        # Collection exists; update its validator
        db.command({
            "collMod": COLL_NAME,
            "validator": validation_schema,
            "validationLevel": "moderate"
        })
        print(f"🔧 Updated validator for existing collection '{COLL_NAME}'.")

def ensure_indexes():
    """Create necessary indexes (idempotent)."""
    if not CONNECTION_OK:
        print("❌ Cannot create indexes - no database connection")
        return
        
    # 1) App-level primary key
    coll.create_index([("soil_key", ASCENDING)], unique=True, name="uniq_soil_key")
    # 2) Helpful lookups
    coll.create_index([("aliases", ASCENDING)], name="aliases_idx")
    coll.create_index([("regions.state", ASCENDING)], name="regions_state_idx")
    # 3) Text search across key name fields
    coll.create_index(
        [("soil_name", TEXT), ("aliases", TEXT), ("favoured_crops", TEXT)],
        name="text_name_alias_crops"
    )
    print("✅ Indexes ensured.")

# --------------------------------------------------------------------
# 3) Optional helpers for later steps (no production data inserted here)
# --------------------------------------------------------------------
def normalize_soil_key(k: str) -> str:
    """Lowercase, trim spaces, replace spaces with hyphens (safe app-level key)."""
    return "-".join(k.strip().lower().split())

def upsert_soil_profile(doc: dict):
    """Upsert a single soil profile (use in Part 2)."""
    if not CONNECTION_OK:
        print("❌ Cannot upsert soil profile - no database connection")
        return
        
    # Ensure soil_key exists and normalized
    if "soil_key" not in doc or not doc["soil_key"]:
        raise ValueError("soil_key is required")
    doc["soil_key"] = normalize_soil_key(doc["soil_key"])

    # Set metadata
    doc.setdefault("version", "v1")
    # Prefer BSON Date; if string is provided, we keep it as-is (validator accepts both)
    doc["updated_at"] = dt.datetime.utcnow()

    res = coll.update_one(
        {"soil_key": doc["soil_key"]},
        {"$set": doc},
        upsert=True
    )
    if res.upserted_id:
        print(f"➕ Inserted new soil profile: {doc['soil_key']}")
    else:
        print(f"♻️  Updated soil profile: {doc['soil_key']}")

def get_by_soil_key(soil_key: str):
    """Quick lookup by primary retrieval key."""
    if not CONNECTION_OK:
        print("❌ Cannot query soil profile - no database connection")
        return None
    return coll.find_one({"soil_key": normalize_soil_key(soil_key)})

# --------------------------------------------------------------------
# 4) Run setup
# --------------------------------------------------------------------
if __name__ == "__main__":
    # Connection test is already done above
    if CONNECTION_OK:
        ensure_collection_with_validation()
        ensure_indexes()
        print("✅ Setup complete for kisan_ai.soil_profiles.")
    else:
        print("❌ Setup incomplete due to connection issues.")
        print("🔧 Please check your MongoDB Atlas connection, network, or credentials.")
        print("📋 However, the script structure is ready and will work once connection is restored.")

    # --- (Optional) sanity test with a minimal placeholder doc (commented) ---
    """
    sample = {
        "soil_key": "black",
        "soil_name": "Black Soil",
        "aliases": ["Regur", "Vertisol"],
        "color": ["dark gray", "black"],
        "texture": "clay to clay loam",
        "structure": "well aggregated; shrink–swell cracks in dry season",
        "physical_properties": {
            "bulk_density_g_cm3": 1.2,
            "infiltration_rate_mm_hr": 5,
            "erosion_risk": "low to moderate"
        },
        "chemical_properties": {
            "pH": { "min": 7.2, "max": 8.5 },
            "cation_exchange_capacity_cmolkg": { "min": 30, "max": 60 },
            "organic_matter_pct": { "min": 0.5, "max": 1.5 },
            "salinity_dS_m": { "max": 2 },
            "sodicity_ESP": { "max": 15 },
            "free_CaCO3_pct": { "min": 2, "max": 8 }
        },
        "water_holding_capacity_pct": { "min": 45, "max": 60 },
        "nutrients_rich_in": ["Ca", "Mg"],
        "nutrients_deficient_in": ["N", "P", "Zn", "S"],
        "favoured_crops": ["cotton", "soybean", "sorghum", "pigeon pea", "wheat"],
        "favoured_seasons": ["Kharif", "Rabi"],
        "drainage": "poor to moderately well",
        "typical_depth_cm": { "min": 50, "max": 150 },
        "regions": [
            { "state": "Maharashtra", "notes": "Deccan plateau belts" },
            { "state": "Madhya Pradesh" },
            { "state": "Gujarat" },
            { "state": "Telangana" },
            { "state": "Karnataka" }
        ],
        "hazards": ["waterlogging", "salinity", "crusting"],  # <--- added
        "notes": "High shrink–swell; avoid tillage when wet; cracks help aeration in dry season.",
        "sources": ["internal_curation_v1"]
    }
    upsert_soil_profile(sample)
    print(get_by_soil_key("black"))
    """
    print("✅ Setup complete for kisan_ai.soil_profiles.")
