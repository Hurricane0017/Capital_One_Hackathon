#!/usr/bin/env python3
"""
Farmer Input Processor - Step 1
Converts raw English text from farmers into structured JSON format
and stores in MongoDB farmer_profiles collection.

Author: Nikhil Mishra
Date: August 17, 2025
"""

import json
import re
import os
from datetime import datetime
from typing import Dict, Any, Optional
import pymongo
from pymongo import MongoClient
from pymongo.server_api import ServerApi
import logging
import certifi
from dotenv import load_dotenv

# Import the LLM client
from llm_client import LLMClient

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FarmerInputProcessor:
    """
    Processes raw English text from farmers and converts to structured JSON format.
    Stores the processed data in MongoDB farmer_profiles collection.
    """
    
    def __init__(self):
        """Initialize the processor with MongoDB Atlas connection and LLM client."""
        self.llm_client = LLMClient()
        
        # Get MongoDB URI from environment
        self.mongo_uri = os.getenv("MONGODB_URI")
        self.db_name = os.getenv("DATABASE_NAME", "kisan_ai")
        
        if not self.mongo_uri:
            raise ValueError("MONGODB_URI not found in environment variables. Please check your .env file.")
        
        self.client = None
        self.db = None
        self.farmer_profiles = None
        
        # Connect to database
        self._connect_database()
    
    def _connect_database(self):
        """Connect to MongoDB Atlas database."""
        try:
            # Connect to MongoDB Atlas using the same pattern as pest_profile_db.py
            self.client = MongoClient(
                self.mongo_uri,
                server_api=ServerApi("1"),
                serverSelectionTimeoutMS=20000,
                tls=True,
                tlsCAFile=certifi.where(),
            )
            
            # Test the connection
            self.client.admin.command('ping')
            
            self.db = self.client[self.db_name]
            self.farmer_profiles = self.db["farmer_profiles"]
            
            # Create index on phone number (primary key)
            self.farmer_profiles.create_index("phone", unique=True)
            
            logger.info(f"✅ Connected to MongoDB Atlas database: {self.db_name}")
        except Exception as e:
            logger.error(f"❌ Failed to connect to MongoDB Atlas: {e}")
            logger.error("🔧 Check: Internet connection, MongoDB URI, IP allowlist, credentials")
            raise
    
    def process_farmer_text(self, raw_text: str) -> Dict[str, Any]:
        """
        Process raw English text from farmer and convert to structured JSON.
        
        Args:
            raw_text (str): Raw English text from farmer
            
        Returns:
            Dict[str, Any]: Structured farmer profile data
        """
        logger.info("Processing farmer input text...")
        
        # First, try LLM-based extraction
        try:
            structured_data = self._extract_with_llm(raw_text)
            
            # Validate the extracted data
            if self._validate_farmer_data(structured_data):
                return structured_data
            else:
                logger.warning("LLM extraction validation failed, trying regex fallback")
                
        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
        
        # Fallback to regex-based extraction
        try:
            structured_data = self._extract_with_regex(raw_text)
            return structured_data
        except Exception as e:
            logger.error(f"Regex extraction failed: {e}")
            raise Exception("Failed to extract farmer data from input text")
    
    def _extract_with_llm(self, raw_text: str) -> Dict[str, Any]:
        """Extract farmer data using LLM."""
        
        prompt = f"""
You are an expert agricultural data processor. Extract structured information from the following farmer's text and convert it to JSON format.

IMPORTANT INSTRUCTIONS:
1. Extract ALL information mentioned in the text
2. Convert area measurements to hectares (1 acre = 0.4047 hectares)
3. Parse dates in ISO format (YYYY-MM-DDTHH:MM:SS)
4. Identify the main query/question from the farmer
5. Use "hi" as default language_spoken for Indian farmers
6. Map goals to: "maximize_profit", "reduce_risk", "sustainable_farming"
7. Map advice frequency to: "daily", "twice_week", "weekly", "monthly"
8. Map preferred time to: "morning", "afternoon", "evening"

FARMER TEXT:
{raw_text}

Extract the information and format it as JSON with this exact structure:
{{
  "name": "farmer's name",
  "phone": "phone number (digits only)",
  "pincode": "PIN code",
  "consent": true/false,
  "land_total_ha": float (in hectares),
  "land_cultivated_ha": float (in hectares),
  "irrigated_ha": float (in hectares),
  "rainfed_ha": float (in hectares),
  "soil_type": "soil type (capitalize first letter)",
  "water_source": "water source",
  "irrigation_method": "irrigation method",
  "crops": [
    {{
      "crop": "crop name",
      "variety": "variety name",
      "area_ha": float,
      "season": "season name",
      "sowing_date": "YYYY-MM-DDTHH:MM:SS",
      "expected_harvest_text": "harvest description"
    }}
  ],
  "budget": {{
    "cash_on_hand_inr": integer,
    "planned_loan_inr": integer
  }},
  "insurance": "insurance scheme name",
  "market": "market name",
  "preferences": {{
    "goal": "goal type",
    "advice_frequency": "frequency",
    "preferred_time": "time preference"
  }},
  "assets": {{
    "machinery": ["list of machinery"],
    "storage_text": "storage description",
    "sprayer": true/false
  }},
  "language_spoken": "hi",
  "farmer_query": "main question or request from farmer"
}}

Return ONLY the JSON, no other text.
"""
        
        try:
            response = self.llm_client.call_text_llm(prompt, temperature=0.3)
            
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_text = json_match.group()
                structured_data = json.loads(json_text)
                
                # Add metadata
                structured_data["created_at"] = datetime.now().isoformat()
                structured_data["updated_at"] = datetime.now().isoformat()
                structured_data["source"] = "llm_extraction"
                
                logger.info("Successfully extracted data using LLM")
                return structured_data
            else:
                raise Exception("No valid JSON found in LLM response")
                
        except Exception as e:
            logger.error(f"LLM extraction error: {e}")
            raise
    
    def _extract_with_regex(self, raw_text: str) -> Dict[str, Any]:
        """Extract farmer data using regex patterns (fallback method)."""
        
        logger.info("Using regex fallback for data extraction")
        
        # Initialize default structure
        structured_data = {
            "name": "",
            "phone": "",
            "pincode": "",
            "consent": True,
            "land_total_ha": 0.0,
            "land_cultivated_ha": 0.0,
            "irrigated_ha": 0.0,
            "rainfed_ha": 0.0,
            "soil_type": "",
            "water_source": "",
            "irrigation_method": "",
            "crops": [],
            "budget": {
                "cash_on_hand_inr": 0,
                "planned_loan_inr": 0
            },
            "insurance": "",
            "market": "",
            "preferences": {
                "goal": "maximize_profit",
                "advice_frequency": "weekly",
                "preferred_time": "morning"
            },
            "assets": {
                "machinery": [],
                "storage_text": "",
                "sprayer": False
            },
            "language_spoken": "hi",
            "farmer_query": "",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "source": "regex_extraction"
        }
        
        # Extract name
        name_patterns = [
            r"[Mm]y name is ([^,\n]+)",
            r"[Nn]ame[:\s]+([^,\n]+)",
            r"I am ([^,\n]+)"
        ]
        for pattern in name_patterns:
            match = re.search(pattern, raw_text)
            if match:
                structured_data["name"] = match.group(1).strip()
                break
        
        # Extract phone
        phone_match = re.search(r"mobile[:\s]+(\d{10})", raw_text)
        if phone_match:
            structured_data["phone"] = phone_match.group(1)
        
        # Extract PIN code
        pin_match = re.search(r"PIN[:\s]+(\d{6})", raw_text)
        if pin_match:
            structured_data["pincode"] = pin_match.group(1)
        
        # Extract land areas (convert acres to hectares)
        total_land_match = re.search(r"(\d+(?:\.\d+)?)\s+acres?\s+in\s+total", raw_text)
        if total_land_match:
            structured_data["land_total_ha"] = float(total_land_match.group(1)) * 0.4047
        
        cultivated_match = re.search(r"cultivating\s+(\d+(?:\.\d+)?)\s+acres?", raw_text)
        if cultivated_match:
            structured_data["land_cultivated_ha"] = float(cultivated_match.group(1)) * 0.4047
        
        irrigated_match = re.search(r"(\d+(?:\.\d+)?)\s+acres?\s+irrigated", raw_text)
        if irrigated_match:
            structured_data["irrigated_ha"] = float(irrigated_match.group(1)) * 0.4047
        
        rainfed_match = re.search(r"(\d+(?:\.\d+)?)\s+acres?\s+rainfed", raw_text)
        if rainfed_match:
            structured_data["rainfed_ha"] = float(rainfed_match.group(1)) * 0.4047
        
        # Extract soil type
        soil_match = re.search(r"[Ss]oil is ([^.\n]+)", raw_text)
        if soil_match:
            structured_data["soil_type"] = soil_match.group(1).strip().capitalize()
        
        # Extract water source
        water_match = re.search(r"[Ww]ater source is ([^;\n]+)", raw_text)
        if water_match:
            structured_data["water_source"] = water_match.group(1).strip().lower()
        
        # Extract irrigation method
        irrigation_match = re.search(r"irrigation is ([^;\n]+)", raw_text)
        if irrigation_match:
            structured_data["irrigation_method"] = irrigation_match.group(1).strip().lower()
        
        # Extract crop information
        crop_match = re.search(r"I planted ([^,]+),?\s*variety ([^,]+)", raw_text)
        if crop_match:
            crop_data = {
                "crop": crop_match.group(1).strip().lower(),
                "variety": crop_match.group(2).strip(),
                "area_ha": structured_data["land_cultivated_ha"],
                "season": "Kharif",  # Default
                "sowing_date": "",
                "expected_harvest_text": ""
            }
            
            # Extract sowing date
            sowing_match = re.search(r"sown on (\d{1,2}\s+\w+\s+\d{4})", raw_text)
            if sowing_match:
                try:
                    sowing_date = datetime.strptime(sowing_match.group(1), "%d %B %Y")
                    crop_data["sowing_date"] = sowing_date.isoformat()
                except:
                    crop_data["sowing_date"] = "2025-07-10T00:00:00"  # Default
            
            # Extract harvest expectation
            harvest_match = re.search(r"expect harvest in ([^.\n]+)", raw_text)
            if harvest_match:
                crop_data["expected_harvest_text"] = harvest_match.group(1).strip()
            
            structured_data["crops"] = [crop_data]
        
        # Extract budget information
        cash_match = re.search(r"₹([\d,]+)\s+cash", raw_text)
        if cash_match:
            cash_amount = cash_match.group(1).replace(",", "")
            structured_data["budget"]["cash_on_hand_inr"] = int(cash_amount)
        
        loan_match = re.search(r"loan of ₹([\d,]+)", raw_text)
        if loan_match:
            loan_amount = loan_match.group(1).replace(",", "")
            structured_data["budget"]["planned_loan_inr"] = int(loan_amount)
        
        # Extract insurance
        insurance_match = re.search(r"enrolled in ([^.\n]+)", raw_text)
        if insurance_match:
            structured_data["insurance"] = insurance_match.group(1).strip()
        
        # Extract market
        market_match = re.search(r"market is ([^.\n]+)", raw_text)
        if market_match:
            structured_data["market"] = market_match.group(1).strip()
        
        # Extract assets
        if "sprayer" in raw_text.lower():
            structured_data["assets"]["sprayer"] = True
            structured_data["assets"]["machinery"].append("sprayer")
        
        # Extract farmer query (usually at the end or contains question words)
        query_patterns = [
            r"Should I ([^?]+\?)",
            r"([^.]*\?)",
            r"I want ([^.\n]+)"
        ]
        
        for pattern in query_patterns:
            matches = re.findall(pattern, raw_text)
            if matches:
                structured_data["farmer_query"] = matches[-1].strip()  # Take the last question
                break
        
        if not structured_data["farmer_query"]:
            structured_data["farmer_query"] = "General farming guidance needed"
        
        logger.info("Regex extraction completed")
        return structured_data
    
    def _validate_farmer_data(self, data: Dict[str, Any]) -> bool:
        """Validate extracted farmer data."""
        required_fields = ["name", "phone", "pincode"]
        
        for field in required_fields:
            if not data.get(field):
                logger.warning(f"Missing required field: {field}")
                return False
        
        # Validate phone number
        phone = data.get("phone", "").replace("-", "").replace(" ", "")
        if not re.match(r"^\d{10}$", phone):
            logger.warning(f"Invalid phone number: {phone}")
            return False
        
        # Validate PIN code
        pincode = data.get("pincode", "")
        if not re.match(r"^\d{6}$", pincode):
            logger.warning(f"Invalid PIN code: {pincode}")
            return False
        
        return True
    
    def store_farmer_profile(self, farmer_data: Dict[str, Any]) -> bool:
        """
        Store farmer profile in MongoDB using phone number as primary key.
        
        Args:
            farmer_data (Dict[str, Any]): Structured farmer profile data
            
        Returns:
            bool: True if stored successfully, False otherwise
        """
        try:
            phone = farmer_data["phone"]
            
            # Update timestamp
            farmer_data["updated_at"] = datetime.now().isoformat()
            
            # Upsert (update if exists, insert if not)
            result = self.farmer_profiles.replace_one(
                {"phone": phone},
                farmer_data,
                upsert=True
            )
            
            if result.upserted_id:
                logger.info(f"New farmer profile created for phone: {phone}")
            else:
                logger.info(f"Farmer profile updated for phone: {phone}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to store farmer profile: {e}")
            return False
    
    def process_and_store(self, raw_text: str) -> Dict[str, Any]:
        """
        Complete pipeline: process raw text and store in database.
        
        Args:
            raw_text (str): Raw English text from farmer
            
        Returns:
            Dict[str, Any]: Processed farmer profile data
        """
        logger.info("Starting complete farmer input processing pipeline...")
        
        try:
            # Step 1: Process text to structured data
            structured_data = self.process_farmer_text(raw_text)
            
            # Step 2: Store in database
            if self.store_farmer_profile(structured_data):
                logger.info("Farmer input processing completed successfully")
                return {
                    "status": "success",
                    "farmer_data": structured_data,
                    "phone": structured_data["phone"],
                    "message": "Farmer profile processed and stored successfully"
                }
            else:
                return {
                    "status": "error",
                    "message": "Failed to store farmer profile in database"
                }
                
        except Exception as e:
            logger.error(f"Complete processing pipeline failed: {e}")
            return {
                "status": "error",
                "message": f"Processing failed: {str(e)}"
            }
    
    def get_farmer_profile(self, phone: str) -> Optional[Dict[str, Any]]:
        """Retrieve farmer profile by phone number."""
        try:
            profile = self.farmer_profiles.find_one({"phone": phone})
            if profile:
                # Remove MongoDB ObjectId for JSON serialization
                profile.pop("_id", None)
                return profile
            return None
        except Exception as e:
            logger.error(f"Failed to retrieve farmer profile: {e}")
            return None
    
    def close_connection(self):
        """Close database connection."""
        if self.client:
            self.client.close()
            logger.info("Database connection closed")


# Example usage and testing
if __name__ == "__main__":
    print("🌾 FARMER INPUT PROCESSOR - STEP 1")
    print("=" * 50)
    
    try:
        # Test with the provided examples
        processor = FarmerInputProcessor()
        
        # Test case 1: Specific query
        test_text_1 = """My name is Ramesh Kumar, mobile 9876543210, PIN 226010. I agree to store my answers. I farm 3 acres in total; this season I am cultivating 2.5 acres. It is mixed: about 1.5 acres irrigated and 1 acre rainfed. Soil is alluvial. Water source is borewell; irrigation is drip on the irrigated part. This is Kharif. I planted soybean, variety JS-335, sown on 10 July 2025; I expect harvest in late October. Seeds used 40 kg; fertilizers DAP 50 kg and urea 30 kg. I noticed pod borer last year, nothing serious yet. I have knapsack sprayer. I have ₹55,000 cash and could take a loan of ₹30,000. I am enrolled in PMFBY. Nearest market is Malihabad mandi. Priority is maximize profit but avoid big risk. Please send advice twice a week, evening is best. Should I plan irrigation in the next 7 days for my soybean crop, given the weather forecast for PIN 226010?"""
        
        print("Testing with MongoDB integration...")
        
        result = processor.process_and_store(test_text_1)
        print(f"Processing result: {result['status']}")
        
        if result['status'] == 'success':
            print(f"Farmer phone: {result['phone']}")
            print(f"Message: {result['message']}")
            
            # Retrieve and display stored profile
            stored_profile = processor.get_farmer_profile(result['phone'])
            if stored_profile:
                print("\n✅ Successfully stored and retrieved from MongoDB!")
                print(f"Stored farmer: {stored_profile['name']}")
                print(f"Crop: {stored_profile['crops'][0]['crop']}")
                print(f"Query: {stored_profile['farmer_query'][:100]}...")
        
        processor.close_connection()
        
    except Exception as e:
        print(f"❌ MongoDB Atlas connection failed: {e}")
        print("\n🔧 SOLUTION OPTIONS:")
        print("1. Check your .env file contains MONGODB_URI")
        print("2. Verify internet connection")
        print("3. Check MongoDB Atlas IP allowlist (allow 0.0.0.0/0 for testing)")
        print("4. Verify MongoDB Atlas credentials")
        print("\n5. Use the test version without MongoDB:")
        print("   python test_step1.py")

# Next we will check if the query from farmer is a specific one that can be answered by

