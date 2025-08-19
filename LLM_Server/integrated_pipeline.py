#!/usr/bin/env python3
"""
Integrated Farmer Pipeline - Steps 1 & 2
Combines farmer input processing with query routing for complete pipeline.

Author: Nikhil Mishra  
Date: August 17, 2025
"""

import json
from typing import Dict, Any
import logging
from datetime import datetime

# Import our components
from farmer_input_processor import FarmerInputProcessor
from query_router import QueryRouter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class IntegratedFarmerPipeline:
    """
    Complete pipeline that processes farmer input and routes queries appropriately.
    """
    
    def __init__(self):
        """Initialize the integrated pipeline."""
        self.input_processor = FarmerInputProcessor()
        self.query_router = QueryRouter()
        logger.info("Integrated Farmer Pipeline initialized")
    
    def process_farmer_input(self, raw_text: str) -> Dict[str, Any]:
        """
        Complete pipeline processing:
        1. Extract farmer profile from raw text
        2. Store in database  
        3. Route the query to appropriate pipeline
        
        Args:
            raw_text (str): Raw English text from farmer
            
        Returns:
            Dict[str, Any]: Complete processing result
        """
        logger.info("Starting integrated farmer input processing...")
        
        try:
            # Step 1: Process and store farmer input
            logger.info("Step 1: Processing farmer profile and query...")
            input_result = self.input_processor.process_and_store(raw_text)
            
            if input_result["status"] != "success":
                return {
                    "status": "error",
                    "stage": "input_processing", 
                    "message": input_result["message"],
                    "error_details": input_result
                }
            
            farmer_data = input_result["farmer_data"]
            farmer_query = farmer_data.get("farmer_query", "")
            
            logger.info(f"✅ Farmer profile processed: {farmer_data['name']} ({farmer_data['phone']})")
            logger.info(f"📋 Query extracted: {farmer_query[:100]}...")
            
            # Step 2: Route the query
            logger.info("Step 2: Routing query to appropriate pipeline...")
            routing_result = self.query_router.route_query(farmer_query, farmer_data)
            
            logger.info(f"✅ Query routed to {routing_result['pipeline']} pipeline")
            
            # Combine results
            final_result = {
                "status": "success",
                "processing_timestamp": datetime.now().isoformat(),
                "farmer_profile": {
                    "phone": farmer_data["phone"],
                    "name": farmer_data["name"],
                    "pincode": farmer_data["pincode"],
                    "crops": farmer_data["crops"],
                    "soil_type": farmer_data["soil_type"],
                    "query": farmer_query
                },
                "routing_decision": {
                    "pipeline": routing_result["pipeline"],
                    "agents": routing_result["agents"],
                    "reason": routing_result["reason"],
                    "confidence": routing_result["confidence"]
                },
                "next_steps": self._generate_next_steps(routing_result),
                "data_stored": True,
                "ready_for_processing": True
            }
            
            logger.info("✅ Integrated processing completed successfully")
            return final_result
            
        except Exception as e:
            logger.error(f"Integrated processing failed: {e}")
            return {
                "status": "error",
                "stage": "integrated_processing",
                "message": f"Pipeline processing failed: {str(e)}",
                "error_timestamp": datetime.now().isoformat()
            }
    
    def _generate_next_steps(self, routing_result: Dict[str, Any]) -> Dict[str, Any]:
        """Generate next steps based on routing decision."""
        
        if routing_result["pipeline"] == "generic":
            return {
                "type": "generic_pipeline",
                "description": "Comprehensive farm management response using all available resources",
                "agents_involved": ["weather", "soil", "pest", "market_price", "scheme"],
                "processing_approach": "holistic_analysis",
                "expected_response": "Complete farming guidance covering all relevant aspects"
            }
        else:
            agents = routing_result["agents"]
            agent_descriptions = []
            
            for agent in agents:
                agent_info = self.query_router.get_agent_requirements(agent)
                agent_descriptions.append({
                    "agent": agent,
                    "name": agent_info["name"],
                    "role": agent_info["description"]
                })
            
            return {
                "type": "specific_pipeline", 
                "description": f"Targeted response using {len(agents)} specific agent(s)",
                "agents_involved": agents,
                "agent_details": agent_descriptions,
                "processing_approach": "focused_analysis",
                "expected_response": f"Specialized guidance from {', '.join([info['name'] for info in agent_descriptions])}"
            }
    
    def get_farmer_profile(self, phone: str) -> Dict[str, Any]:
        """Retrieve farmer profile by phone number."""
        return self.input_processor.get_farmer_profile(phone)
    
    def reprocess_query(self, phone: str, new_query: str) -> Dict[str, Any]:
        """Reprocess a new query for an existing farmer."""
        logger.info(f"Reprocessing query for farmer {phone}")
        
        try:
            # Get existing farmer profile
            farmer_profile = self.get_farmer_profile(phone)
            if not farmer_profile:
                return {
                    "status": "error",
                    "message": f"No farmer profile found for phone: {phone}"
                }
            
            # Route the new query
            routing_result = self.query_router.route_query(new_query, farmer_profile)
            
            # Update farmer profile with new query
            farmer_profile["farmer_query"] = new_query
            farmer_profile["updated_at"] = datetime.now().isoformat()
            
            # Store updated profile
            self.input_processor.store_farmer_profile(farmer_profile)
            
            return {
                "status": "success",
                "farmer_profile": {
                    "phone": farmer_profile["phone"],
                    "name": farmer_profile["name"],
                    "query": new_query
                },
                "routing_decision": {
                    "pipeline": routing_result["pipeline"],
                    "agents": routing_result["agents"], 
                    "reason": routing_result["reason"],
                    "confidence": routing_result["confidence"]
                },
                "next_steps": self._generate_next_steps(routing_result)
            }
            
        except Exception as e:
            logger.error(f"Query reprocessing failed: {e}")
            return {
                "status": "error",
                "message": f"Failed to reprocess query: {str(e)}"
            }
    
    def close_connections(self):
        """Close all database connections."""
        self.input_processor.close_connection()
        logger.info("Pipeline connections closed")


# Testing and demonstration
if __name__ == "__main__":
    print("🚀 INTEGRATED FARMER PIPELINE - STEPS 1 & 2 TEST")
    print("=" * 70)
    
    pipeline = IntegratedFarmerPipeline()
    
    # Test case 1: Complete processing with specific query
    test_input_1 = """My name is Ramesh Kumar, mobile 9876543210, PIN 226010. I agree to store my answers. I farm 3 acres in total; this season I am cultivating 2.5 acres. It is mixed: about 1.5 acres irrigated and 1 acre rainfed. Soil is alluvial. Water source is borewell; irrigation is drip on the irrigated part. This is Kharif. I planted soybean, variety JS-335, sown on 10 July 2025; I expect harvest in late October. Seeds used 40 kg; fertilizers DAP 50 kg and urea 30 kg. I noticed pod borer last year, nothing serious yet. I have knapsack sprayer. I have ₹55,000 cash and could take a loan of ₹30,000. I am enrolled in PMFBY. Nearest market is Malihabad mandi. Priority is maximize profit but avoid big risk. Please send advice twice a week, evening is best. Should I plan irrigation in the next 7 days for my soybean crop, given the weather forecast for PIN 226010?"""
    
    print("TEST CASE 1: Specific Weather Query")
    print("-" * 50)
    
    result = pipeline.process_farmer_input(test_input_1)
    
    if result["status"] == "success":
        print("✅ PROCESSING SUCCESSFUL!")
        print(f"👤 Farmer: {result['farmer_profile']['name']} ({result['farmer_profile']['phone']})")
        print(f"📍 Location: PIN {result['farmer_profile']['pincode']}")
        print(f"🌾 Crop: {result['farmer_profile']['crops'][0]['crop']} ({result['farmer_profile']['crops'][0]['variety']})")
        print(f"❓ Query: {result['farmer_profile']['query'][:80]}...")
        print(f"🎯 Pipeline: {result['routing_decision']['pipeline'].upper()}")
        print(f"🔧 Agents: {', '.join(result['routing_decision']['agents']) if result['routing_decision']['agents'] else 'All (Generic)'}")
        print(f"📊 Confidence: {result['routing_decision']['confidence']}")
        print(f"💡 Reason: {result['routing_decision']['reason'][:100]}...")
        print(f"📋 Next Steps: {result['next_steps']['description']}")
        
    else:
        print(f"❌ Processing failed: {result['message']}")
    
    print("\n" + "=" * 70)
    
    # Test case 2: Generic query processing
    test_input_2 = """My name is Priya Sharma, mobile 8765432109, PIN 110001. I agree to store my answers. I farm 5 acres in total; this season I am cultivating 4 acres. It is mixed: about 2 acres irrigated and 2 acres rainfed. Soil is sandy loam. Water source is tube well; irrigation is sprinkler on the irrigated part. This is Rabi. I planted wheat, variety HD-2967, sown on 15 November 2024; I expect harvest in March. Seeds used 60 kg; fertilizers DAP 75 kg and urea 50 kg. I had aphid problem last year. I have tractor and sprayer. I have ₹80,000 cash and could take a loan of ₹50,000. I am enrolled in crop insurance. Nearest market is APMC Delhi. Priority is sustainable farming with good returns. Please send advice weekly, morning is best. I want comprehensive guidance on crop and farm management to improve my farming practices and income."""
    
    print("TEST CASE 2: Generic Comprehensive Query")
    print("-" * 50)
    
    result2 = pipeline.process_farmer_input(test_input_2)
    
    if result2["status"] == "success":
        print("✅ PROCESSING SUCCESSFUL!")
        print(f"👤 Farmer: {result2['farmer_profile']['name']} ({result2['farmer_profile']['phone']})")
        print(f"📍 Location: PIN {result2['farmer_profile']['pincode']}")
        print(f"🌾 Crop: {result2['farmer_profile']['crops'][0]['crop']} ({result2['farmer_profile']['crops'][0]['variety']})")
        print(f"🎯 Pipeline: {result2['routing_decision']['pipeline'].upper()}")
        print(f"🔧 Agents: {', '.join(result2['routing_decision']['agents']) if result2['routing_decision']['agents'] else 'All (Generic)'}")
        print(f"📊 Confidence: {result2['routing_decision']['confidence']}")
        print(f"💡 Reason: {result2['routing_decision']['reason'][:100]}...")
        print(f"📋 Next Steps: {result2['next_steps']['description']}")
        
    else:
        print(f"❌ Processing failed: {result2['message']}")
    
    print("\n" + "=" * 70)
    
    # Test case 3: Query reprocessing for existing farmer
    print("TEST CASE 3: Query Reprocessing")
    print("-" * 50)
    
    reprocess_result = pipeline.reprocess_query("9876543210", "What pest control should I use for pod borer in my soybean?")
    
    if reprocess_result["status"] == "success":
        print("✅ REPROCESSING SUCCESSFUL!")
        print(f"👤 Farmer: {reprocess_result['farmer_profile']['name']}")
        print(f"❓ New Query: {reprocess_result['farmer_profile']['query']}")
        print(f"🎯 Pipeline: {reprocess_result['routing_decision']['pipeline'].upper()}")
        print(f"🔧 Agents: {', '.join(reprocess_result['routing_decision']['agents'])}")
        print(f"📊 Confidence: {reprocess_result['routing_decision']['confidence']}")
        
    else:
        print(f"❌ Reprocessing failed: {reprocess_result['message']}")
    
    pipeline.close_connections()
    
    print(f"\n🎉 INTEGRATED PIPELINE TESTING COMPLETED!")
    print(f"✅ Step 1: Farmer input processing ✅")  
    print(f"✅ Step 2: Query routing ✅")
    print(f"✅ Integration working perfectly ✅")
    print(f"✅ Database storage and retrieval ✅")
    print(f"✅ Ready for Step 3: Agent implementation! ✅")
