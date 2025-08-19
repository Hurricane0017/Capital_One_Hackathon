#!/usr/bin/env python3
"""
Pest Agent - Step 3.c
Comprehensive pest agent that provides pest identification and management guidance for both
specific pipeline (targeted pest queries) and generic pipeline (comprehensive pest guidance) scenarios.

Key Capabilities:
- Identify pests from farmer descriptions, symptoms, and crop/soil context using LLM
- Retrieve detailed pest data from MongoDB pest_profiles collection
- Correlate pests with farmer's crop and soil type for targeted recommendations
- Provide context-aware integrated pest management strategies
- Handle both specific queries and generic pest recommendations

Author: Nikhil Mishra
Date: August 17, 2025
"""

import os
import sys
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

# Import LLM client
from llm_client import LLMClient
from logging_config import setup_logging

# Configure logging
logger = setup_logging('PestAgent')

# Import pest database functions using relative path
try:
    # Add the db_uploading directory to path
    db_path = os.path.join(os.path.dirname(__file__), 'db_uploading')
    if db_path not in sys.path:
        sys.path.append(db_path)
    
    from db_uploading.pest_profile_db import get_by_common_name, get_by_pest_key, coll, client, db
    CONNECTION_OK = True
    logger.info("Pest database connection imported successfully")
except ImportError as e:
    logger.warning(f"Could not import pest database functions: {e}")
    CONNECTION_OK = False
    # Create mock functions for testing
    def get_by_common_name(name): return None
    def get_by_pest_key(key): return None
    coll = None
    client = None
    db = None

class PestAgent:
    """
    Comprehensive Pest Agent for agricultural pest identification and management.
    
    Handles both specific pipeline (targeted pest queries) and generic pipeline 
    (comprehensive pest guidance) scenarios.
    """
    
    def __init__(self):
        """Initialize the Pest Agent with required clients."""
        self.llm_client = LLMClient(logger=logger)
        logger.info("Pest Agent initialized")
        
        # Regional pest-crop mapping for fallback pest determination
        self.regional_pest_mapping = {
            "rice": {
                "common_pests": ["Brown Planthopper", "Rice Gall Midge", "Rice Leaf Folder", "Yellow Stem Borer"],
                "soil_specific": {
                    "alluvial": ["Brown Planthopper", "Yellow Stem Borer"],
                    "clay": ["Rice Gall Midge", "Brown Planthopper"],
                    "loamy": ["Rice Leaf Folder", "Yellow Stem Borer"]
                }
            },
            "cotton": {
                "common_pests": ["Pink Bollworm", "Cotton Aphid", "Cotton Whitefly", "Cotton Thrips"],
                "soil_specific": {
                    "black": ["Pink Bollworm", "Cotton Aphid"],
                    "red": ["Cotton Whitefly", "Cotton Thrips"], 
                    "alluvial": ["Cotton Aphid", "Pink Bollworm"]
                }
            },
            "wheat": {
                "common_pests": ["Wheat Aphid", "Wheat Armyworm", "Wheat Termite"],
                "soil_specific": {
                    "alluvial": ["Wheat Aphid", "Wheat Armyworm"],
                    "black": ["Wheat Termite", "Wheat Aphid"],
                    "red": ["Wheat Armyworm", "Wheat Termite"]
                }
            },
            "coffee": {
                "common_pests": ["Coffee Berry Borer", "Coffee White Stem Borer"],
                "soil_specific": {
                    "red": ["Coffee Berry Borer"],
                    "forest": ["Coffee White Stem Borer"],
                    "laterite": ["Coffee Berry Borer"]
                }
            },
            "sugarcane": {
                "common_pests": ["Sugarcane Pyrilla", "Early Shoot Borer", "Top Borer"],
                "soil_specific": {
                    "alluvial": ["Early Shoot Borer", "Top Borer"],
                    "black": ["Sugarcane Pyrilla"],
                    "red": ["Early Shoot Borer"]
                }
            }
        }
    
    def process_query(self, query: str, farmer_profile: Dict[str, Any] = None, 
                     pipeline_type: str = "specific") -> Dict[str, Any]:
        """
        Process farmer pest-related query based on pipeline type.
        
        Args:
            query (str): Farmer's pest query
            farmer_profile (Dict[str, Any]): Farmer profile with crops and location
            pipeline_type (str): "specific" or "generic"
            
        Returns:
            Dict[str, Any]: Pest analysis and recommendations
        """
        logger.info(f"Processing {pipeline_type} pest query: {query[:100]}...")
        
        try:
            if pipeline_type == "specific":
                return self._process_specific_query(query, farmer_profile or {})
            else:
                return self._process_generic_query(query, farmer_profile or {})
                
        except Exception as e:
            logger.error(f"Error processing pest query: {e}")
            return {
                "success": False,
                "agent": "pest",
                "error": str(e),
                "fallback_message": "Unable to process pest query. Please check pest database connection."
            }
    
    def _process_specific_query(self, query: str, farmer_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Process specific pipeline pest queries with targeted pest identification."""
        
        # Step 1: Identify potential pests from query and farmer context
        identified_pests = self._identify_pests_from_context(query, farmer_profile)
        
        # Step 2: Get pest data from database
        pest_data_list = []
        for pest_name in identified_pests[:3]:  # Limit to top 3 pests
            pest_data = self._get_pest_data(pest_name)
            if pest_data:
                pest_data_list.append(pest_data)
        
        if not pest_data_list:
            return {
                "success": False,
                "agent": "pest",
                "pipeline": "specific",
                "message": "No specific pest data found for your query. Please describe symptoms more clearly."
            }
        
        # Step 3: Generate LLM-based pest analysis
        analysis_result = self._generate_specific_pest_analysis(query, pest_data_list, farmer_profile)
        
        return {
            "success": True,
            "agent": "pest",
            "pipeline": "specific",
            "identified_pests": identified_pests,
            "pest_count": len(pest_data_list),
            "pest_data": pest_data_list,
            "analysis": analysis_result,
            "timestamp": datetime.now().isoformat()
        }
    
    def _process_generic_query(self, query: str, farmer_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Process generic pipeline pest queries for orchestrator coordination."""
        
        # Step 1: Determine relevant pests based on farmer's crops and soil
        relevant_pests = self._get_relevant_pests_for_farmer(farmer_profile)
        
        # Step 2: Get detailed pest data
        pest_data_list = []
        for pest_name in relevant_pests[:5]:  # Get up to 5 relevant pests
            pest_data = self._get_pest_data(pest_name)
            if pest_data:
                pest_data_list.append(pest_data)
        
        # Step 3: Generate orchestrator guidance
        orchestrator_guidance = self._generate_orchestrator_guidance(pest_data_list, farmer_profile)
        
        return {
            "success": True,
            "agent": "pest",
            "pipeline": "generic",
            "relevant_pests": relevant_pests,
            "pest_data_count": len(pest_data_list),
            "orchestrator_guidance": orchestrator_guidance,
            "timestamp": datetime.now().isoformat()
        }
    
    def _identify_pests_from_context(self, query: str, farmer_profile: Dict[str, Any]) -> List[str]:
        """Identify pests using LLM analysis with fallback to crop-soil mapping."""
        
        # Get farmer's crops and soil for context
        crops = [crop.get('crop', '').lower() for crop in farmer_profile.get('crops', [])]
        soil_type = farmer_profile.get('soil_type', '').lower()
        location = f"{farmer_profile.get('district', '')}, {farmer_profile.get('state', '')}"
        
        # Try LLM-based pest identification
        try:
            pest_list = self._identify_pests_with_llm(query, crops, soil_type, location)
            if pest_list:
                logger.info(f"LLM identified pests: {pest_list}")
                return pest_list
        except Exception as e:
            logger.warning(f"LLM pest identification failed: {e}")
        
        # Fallback to crop-soil based pest mapping
        logger.info("Using fallback crop-soil pest determination")
        return self._fallback_pest_determination(crops, soil_type, query)
    
    def _identify_pests_with_llm(self, query: str, crops: List[str], soil_type: str, location: str) -> List[str]:
        """Use LLM to identify pests from query and context."""
        
        # Get available pest names for context
        available_pests = self._get_available_pest_names()
        
        prompt = f"""
You are an expert agricultural entomologist. Analyze the farmer's query and identify the most likely pests based on the described symptoms, crop, and soil conditions.

FARMER'S QUERY: "{query}"

FARMER'S CONTEXT:
- Crops grown: {', '.join(crops) if crops else 'Not specified'}
- Soil type: {soil_type if soil_type else 'Not specified'}
- Location: {location if location.strip(', ') else 'Not specified'}

AVAILABLE PESTS IN DATABASE:
{', '.join(available_pests[:20])}... (and more)

INSTRUCTIONS:
1. Analyze the query for pest symptoms, damage patterns, or direct pest mentions
2. Match symptoms with known pest characteristics
3. Consider crop-pest associations (e.g., Brown Planthopper with rice, Pink Bollworm with cotton)
4. Consider soil-pest relationships if relevant
5. Return EXACT pest names from the available pest list

Return your response as a JSON list of the 3 most likely pest names:
["Pest Name 1", "Pest Name 2", "Pest Name 3"]

If no specific symptoms are described, return the most common pests for the farmer's crops.
Return only the JSON list, no other text.
"""
        
        try:
            response = self.llm_client.call_text_llm(prompt)
            pest_names = json.loads(response.strip())
            
            # Validate pest names exist in our database
            valid_pests = []
            for pest_name in pest_names:
                if self._validate_pest_exists(pest_name):
                    valid_pests.append(pest_name)
            
            return valid_pests[:3]
            
        except Exception as e:
            logger.error(f"LLM pest identification error: {e}")
            return []
    
    def _fallback_pest_determination(self, crops: List[str], soil_type: str, query: str) -> List[str]:
        """Determine pests using crop-soil mapping and query keywords."""
        
        identified_pests = []
        
        # Check for direct pest mentions in query
        query_lower = query.lower()
        pest_keywords = {
            'aphid': ['Cotton Aphid', 'Wheat Aphid', 'Pulse Aphid', 'Tobacco Aphid'],
            'borer': ['Pink Bollworm', 'Coffee Berry Borer', 'Maize Stem Borer', 'Early Shoot Borer'],
            'planthopper': ['Brown Planthopper'],
            'thrips': ['Cotton Thrips', 'Pulse Thrips'],
            'whitefly': ['Cotton Whitefly'],
            'caterpillar': ['Tobacco Caterpillar', 'Jute Hairy Caterpillar'],
            'mite': ['Red Spider Mite', 'Yellow Mite'],
            'termite': ['Wheat Termite'],
            'armyworm': ['Fall Armyworm', 'Wheat Armyworm']
        }
        
        for keyword, pest_names in pest_keywords.items():
            if keyword in query_lower:
                identified_pests.extend(pest_names)
        
        # If direct matches found, return them
        if identified_pests:
            return identified_pests[:3]
        
        # Use crop-based pest determination
        for crop in crops:
            if crop in self.regional_pest_mapping:
                crop_pests = self.regional_pest_mapping[crop]
                
                # Try soil-specific pests first
                if soil_type in crop_pests.get('soil_specific', {}):
                    identified_pests.extend(crop_pests['soil_specific'][soil_type])
                
                # Add common pests for the crop
                identified_pests.extend(crop_pests['common_pests'])
        
        # Remove duplicates and return top 3
        unique_pests = list(dict.fromkeys(identified_pests))
        return unique_pests[:3] if unique_pests else ['Brown Planthopper', 'Cotton Aphid', 'Wheat Aphid']
    
    def _get_relevant_pests_for_farmer(self, farmer_profile: Dict[str, Any]) -> List[str]:
        """Get relevant pests for farmer's crops and soil type for generic pipeline."""
        
        crops = [crop.get('crop', '').lower() for crop in farmer_profile.get('crops', [])]
        soil_type = farmer_profile.get('soil_type', '').lower()
        
        relevant_pests = []
        
        # Get pests for each crop
        for crop in crops:
            if crop in self.regional_pest_mapping:
                crop_pests = self.regional_pest_mapping[crop]
                
                # Add soil-specific pests
                if soil_type in crop_pests.get('soil_specific', {}):
                    relevant_pests.extend(crop_pests['soil_specific'][soil_type])
                
                # Add common pests
                relevant_pests.extend(crop_pests.get('common_pests', []))
        
        # Remove duplicates while preserving order
        unique_pests = list(dict.fromkeys(relevant_pests))
        
        # If no specific crops, return general high-impact pests
        if not unique_pests:
            unique_pests = ['Brown Planthopper', 'Pink Bollworm', 'Cotton Aphid', 'Wheat Aphid', 'Fall Armyworm']
        
        return unique_pests[:5]
    
    def _get_pest_data(self, pest_name: str) -> Optional[Dict[str, Any]]:
        """Retrieve pest data from MongoDB."""
        try:
            # Try exact name match first
            pest_data = get_by_common_name(pest_name)
            
            if not pest_data:
                # Try partial name search
                pest_data = coll.find_one({"common_name": {"$regex": pest_name, "$options": "i"}})
            
            if pest_data:
                # Remove MongoDB _id field and convert datetime objects
                pest_data.pop('_id', None)
                
                # Convert datetime objects to strings for JSON serialization
                def convert_datetime(obj):
                    if isinstance(obj, dict):
                        return {k: convert_datetime(v) for k, v in obj.items()}
                    elif isinstance(obj, list):
                        return [convert_datetime(item) for item in obj]
                    elif hasattr(obj, 'isoformat'):  # datetime objects
                        return obj.isoformat()
                    else:
                        return obj
                
                pest_data = convert_datetime(pest_data)
                logger.info(f"Retrieved pest data for: {pest_name}")
                return pest_data
            else:
                logger.warning(f"No pest data found for: {pest_name}")
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving pest data for {pest_name}: {e}")
            return None
    
    def _generate_specific_pest_analysis(self, query: str, pest_data_list: List[Dict[str, Any]], 
                                       farmer_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Generate LLM-based specific pest analysis."""
        
        try:
            # Prepare context for LLM
            pest_context = []
            for pest_data in pest_data_list:
                pest_context.append({
                    "name": pest_data.get("common_name", ""),
                    "description": pest_data.get("description", ""),
                    "symptoms": pest_data.get("identification", {}).get("physical_signs", []),
                    "crops_affected": pest_data.get("attack_details", {}).get("crops_attacked", []),
                    "management": {
                        "cultural": pest_data.get("management_strategies", {}).get("cultural_methods", []),
                        "biological": pest_data.get("management_strategies", {}).get("biological_control", []),
                        "chemical": pest_data.get("management_strategies", {}).get("chemical_control", {})
                    }
                })
            
            crops = ', '.join([crop.get('crop', '') for crop in farmer_profile.get('crops', [])])
            
            prompt = f"""
You are an expert agricultural entomologist providing pest management advice to an Indian farmer.

FARMER'S QUERY: "{query}"
FARMER'S CROPS: {crops}
LOCATION: {farmer_profile.get('district', '')}, {farmer_profile.get('state', '')}

IDENTIFIED PESTS DATA:
{json.dumps(pest_context, indent=2)}

Provide comprehensive pest management advice with:

1. **Pest Identification Confirmation**: 
   - Which pest(s) most likely match the farmer's description
   - Key symptoms to confirm identification

2. **Immediate Action Plan**:
   - Urgent steps to take within 24-48 hours
   - Damage assessment and monitoring

3. **Management Strategy**:
   - Cultural practices (immediate and long-term)
   - Biological control options available in India
   - Chemical control (if necessary) with specific products and dosages
   - Integrated approach combining multiple methods

4. **Prevention for Future**:
   - Preventive cultural practices
   - Monitoring techniques
   - Seasonal planning

5. **Cost-Effective Solutions**:
   - Budget-friendly options
   - Local availability of treatments
   - Return on investment for different treatments

Make recommendations practical, cost-effective, and suitable for Indian farming conditions.
Use simple language that farmers can understand.
"""
            
            analysis = self.llm_client.call_text_llm(prompt)
            
            # Extract structured recommendations
            recommendations = self._extract_pest_recommendations(analysis, pest_data_list)
            
            return {
                "detailed_analysis": analysis,
                "recommendations": recommendations,
                "management_priority": self._get_management_priority(pest_data_list),
                "cost_estimate": self._estimate_treatment_costs(pest_data_list)
            }
            
        except Exception as e:
            logger.error(f"Error generating specific pest analysis: {e}")
            # Return fallback analysis
            return self._generate_fallback_pest_analysis(pest_data_list)
    
    def _generate_orchestrator_guidance(self, pest_data_list: List[Dict[str, Any]], 
                                      farmer_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive pest guidance for orchestrator coordination."""
        
        if not pest_data_list:
            return {"message": "No pest data available for guidance"}
        
        # Extract key information for orchestration
        pest_summary = []
        priority_pests = []
        management_focus = []
        
        for pest_data in pest_data_list:
            pest_name = pest_data.get("common_name", "")
            max_loss = pest_data.get("impact", {}).get("max_crop_loss_percent", 0)
            
            pest_summary.append({
                "name": pest_name,
                "risk_level": "high" if max_loss > 30 else "medium" if max_loss > 15 else "low",
                "max_crop_loss_percent": max_loss,
                "main_crops_affected": pest_data.get("attack_details", {}).get("crops_attacked", [])
            })
            
            if max_loss > 20:  # High-impact pests
                priority_pests.append(pest_name)
        
        # Generate management focus areas
        management_focus = [
            {
                "category": "monitoring",
                "priority": "high", 
                "focus": "Regular field scouting for early detection",
                "timing": "Weekly during crop growth stages"
            },
            {
                "category": "prevention",
                "priority": "high",
                "focus": "Cultural practices and field sanitation", 
                "timing": "Pre-sowing and post-harvest"
            },
            {
                "category": "biological_control",
                "priority": "medium",
                "focus": "Natural enemy conservation and biocontrol agents",
                "timing": "Throughout growing season"
            },
            {
                "category": "chemical_intervention", 
                "priority": "low",
                "focus": "Targeted application only when threshold reached",
                "timing": "Based on monitoring results"
            }
        ]
        
        return {
            "pest_summary": pest_summary,
            "priority_pests": priority_pests,
            "management_focus": management_focus,
            "seasonal_calendar": self._generate_pest_seasonal_calendar(pest_data_list),
            "integration_points": {
                "weather_dependency": ["Monitor for favorable pest conditions", "Time applications with weather"],
                "soil_considerations": ["Soil moisture affects pest development", "Soil health impacts plant resistance"],
                "crop_stage_critical": ["Most vulnerable growth stages", "Timing of preventive measures"]
            },
            "farmer_actions": self._prioritize_farmer_actions(pest_data_list)
        }
    
    def _get_available_pest_names(self) -> List[str]:
        """Get list of available pest names from database."""
        try:
            pest_names = []
            cursor = coll.find({}, {"common_name": 1})
            for doc in cursor:
                pest_names.append(doc.get("common_name", ""))
            return pest_names
        except Exception as e:
            logger.error(f"Error getting available pest names: {e}")
            # Return fallback list
            return ["Brown Planthopper", "Pink Bollworm", "Cotton Aphid", "Wheat Aphid", "Coffee Berry Borer"]
    
    def _validate_pest_exists(self, pest_name: str) -> bool:
        """Validate if pest exists in database."""
        try:
            result = coll.find_one({"common_name": pest_name})
            return result is not None
        except:
            return False
    
    def _extract_pest_recommendations(self, analysis: str, pest_data_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract structured pest recommendations from analysis."""
        
        recommendations = []
        
        # Extract from pest data
        for pest_data in pest_data_list:
            pest_name = pest_data.get("common_name", "")
            
            # Cultural methods
            cultural_methods = pest_data.get("management_strategies", {}).get("cultural_methods", [])
            if cultural_methods:
                recommendations.append({
                    "category": "cultural",
                    "pest": pest_name,
                    "action": cultural_methods[0] if cultural_methods else "",
                    "priority": "high",
                    "cost": "low"
                })
            
            # Biological control
            biological_control = pest_data.get("management_strategies", {}).get("biological_control", [])
            if biological_control and isinstance(biological_control, list) and biological_control:
                bio_agent = biological_control[0]
                if isinstance(bio_agent, dict):
                    recommendations.append({
                        "category": "biological", 
                        "pest": pest_name,
                        "action": f"Use {bio_agent.get('agent', '')} - {bio_agent.get('method', '')}",
                        "priority": "medium",
                        "cost": "medium"
                    })
            
            # Chemical control (curative)
            chemical_control = pest_data.get("management_strategies", {}).get("chemical_control", {})
            curative = chemical_control.get("curative", [])
            if curative and isinstance(curative, list) and curative:
                chem_treatment = curative[0]
                if isinstance(chem_treatment, dict):
                    recommendations.append({
                        "category": "chemical",
                        "pest": pest_name,
                        "action": f"{chem_treatment.get('pesticide_name', '')} at {chem_treatment.get('dosage', '')}",
                        "priority": "low",
                        "cost": "high",
                        "stage": chem_treatment.get('application_stage', '')
                    })
        
        return recommendations
    
    def _get_management_priority(self, pest_data_list: List[Dict[str, Any]]) -> str:
        """Determine overall management priority based on pest impact."""
        
        max_loss = 0
        for pest_data in pest_data_list:
            pest_loss = pest_data.get("impact", {}).get("max_crop_loss_percent", 0)
            max_loss = max(max_loss, pest_loss)
        
        if max_loss > 40:
            return "critical"
        elif max_loss > 20:
            return "high"
        elif max_loss > 10:
            return "medium"
        else:
            return "low"
    
    def _estimate_treatment_costs(self, pest_data_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Estimate treatment costs from pesticides market data."""
        
        total_cost_range = {"min": 0, "max": 0}
        treatment_options = []
        
        for pest_data in pest_data_list:
            pesticides = pest_data.get("pesticides_market", [])
            for pesticide in pesticides[:2]:  # Top 2 pesticides per pest
                if isinstance(pesticide, dict):
                    cost = pesticide.get("cost_per_unit", {})
                    if isinstance(cost, dict) and "amount" in cost:
                        amount = cost.get("amount", 0)
                        treatment_options.append({
                            "product": pesticide.get("brand_name", ""),
                            "cost_inr": amount,
                            "unit": cost.get("unit", "")
                        })
                        total_cost_range["max"] += amount
        
        total_cost_range["min"] = total_cost_range["max"] * 0.6  # Estimate lower range
        
        return {
            "cost_range_inr": total_cost_range,
            "treatment_options": treatment_options[:3],  # Top 3 options
            "cost_per_hectare_estimate": total_cost_range["max"] // 2
        }
    
    def _generate_pest_seasonal_calendar(self, pest_data_list: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Generate seasonal calendar for pest management."""
        
        calendar = {
            "pre_sowing": ["Field preparation", "Soil treatment", "Seed treatment"],
            "sowing_early_growth": ["Monitor for early pests", "Preventive sprays"],
            "vegetative_growth": ["Regular scouting", "Biological control release"],
            "flowering_fruiting": ["Intensive monitoring", "Targeted interventions"],
            "harvest": ["Final treatments", "Field sanitation"],
            "post_harvest": ["Crop residue management", "Storage pest management"]
        }
        
        return calendar
    
    def _prioritize_farmer_actions(self, pest_data_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prioritize farmer actions based on pest data."""
        
        actions = [
            {
                "action": "Conduct daily field scouting during vulnerable crop stages",
                "priority": "high",
                "timing": "throughout_season",
                "cost": "free"
            },
            {
                "action": "Maintain field sanitation and remove crop residues",
                "priority": "high", 
                "timing": "post_harvest",
                "cost": "low"
            },
            {
                "action": "Use pheromone traps for pest monitoring",
                "priority": "medium",
                "timing": "growing_season",
                "cost": "medium"
            },
            {
                "action": "Apply chemical treatments only when pest threshold reached",
                "priority": "medium",
                "timing": "as_needed",
                "cost": "high"
            }
        ]
        
        return actions
    
    def _generate_fallback_pest_analysis(self, pest_data_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate fallback analysis when LLM is unavailable."""
        
        if not pest_data_list:
            return {"message": "No pest data available for analysis"}
        
        pest_data = pest_data_list[0]  # Use first pest
        
        return {
            "detailed_analysis": f"Pest identified: {pest_data.get('common_name', '')}. " +
                               f"Description: {pest_data.get('description', '')}. " +
                               "Consult with local agricultural extension officer for detailed management advice.",
            "recommendations": self._extract_pest_recommendations("", pest_data_list),
            "management_priority": self._get_management_priority(pest_data_list),
            "cost_estimate": self._estimate_treatment_costs(pest_data_list)
        }


# Testing and demonstration
if __name__ == "__main__":
    print("🐛 PEST AGENT - STEP 3.c TEST")
    print("=" * 60)
    
    # Initialize pest agent
    agent = PestAgent()
    
    # Test farmer profiles with different crop scenarios
    test_profiles = [
        {
            "name": "Rajesh Kumar",
            "district": "Guntur",
            "state": "Andhra Pradesh", 
            "crops": [{"crop": "cotton", "area_ha": 2.0}],
            "soil_type": "black"
        },
        {
            "name": "Suresh Singh",
            "district": "Lucknow",
            "state": "Uttar Pradesh",
            "crops": [{"crop": "wheat", "area_ha": 3.5}],
            "soil_type": "alluvial"
        },
        {
            "name": "Priya Nair", 
            "district": "Alappuzha",
            "state": "Kerala",
            "crops": [{"crop": "rice", "area_ha": 1.5}]
        }
    ]
    
    # Test queries
    test_queries = [
        {
            "query": "My cotton plants have small pink caterpillars inside the bolls, what should I do?",
            "profile_idx": 0,
            "pipeline": "specific",
            "description": "Specific Pink Bollworm identification query"
        },
        {
            "query": "There are small brown insects at the base of my rice plants and the plants are yellowing",
            "profile_idx": 2, 
            "pipeline": "specific",
            "description": "Specific Brown Planthopper identification query"
        },
        {
            "query": "I need comprehensive pest management guidance for my farm",
            "profile_idx": 1,
            "pipeline": "generic", 
            "description": "Generic pest management guidance"
        }
    ]
    
    # Test each scenario
    for i, test_case in enumerate(test_queries, 1):
        profile = test_profiles[test_case["profile_idx"]]
        
        print(f"\n🧪 TEST {i}: {test_case['description']}")
        print(f"Profile: {profile['name']} - {', '.join([c['crop'] for c in profile['crops']])}")
        print(f"Query: {test_case['query']}")
        print("-" * 60)
        
        try:
            result = agent.process_query(
                query=test_case["query"],
                farmer_profile=profile,
                pipeline_type=test_case["pipeline"]
            )
            
            if result.get("success"):
                print(f"✅ Success - Pipeline: {result.get('pipeline')}")
                
                if test_case["pipeline"] == "specific":
                    print(f"🔍 Identified Pests: {result.get('identified_pests', [])}")
                    print(f"📊 Pest Data Count: {result.get('pest_count', 0)}")
                    
                    analysis = result.get("analysis", {})
                    if "management_priority" in analysis:
                        print(f"⚠️ Management Priority: {analysis['management_priority']}")
                    
                    recommendations = analysis.get("recommendations", [])
                    if recommendations:
                        print(f"💡 Top Recommendation: {recommendations[0].get('action', '')[:100]}...")
                
                elif test_case["pipeline"] == "generic":
                    guidance = result.get("orchestrator_guidance", {})
                    pest_summary = guidance.get("pest_summary", [])
                    if pest_summary:
                        print(f"🐛 Relevant Pests: {[p['name'] for p in pest_summary[:3]]}")
                    
                    priority_pests = guidance.get("priority_pests", [])
                    if priority_pests:
                        print(f"⚡ Priority Pests: {priority_pests}")
                    
                    management_focus = guidance.get("management_focus", [])
                    if management_focus:
                        print(f"🎯 Management Focus: {management_focus[0].get('focus', '')}")
            
            else:
                print(f"❌ Failed: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"💥 Exception: {e}")
    
    print(f"\n🎉 STEP 3.c TESTING COMPLETED!")
    print(f"✅ Pest Agent implemented with dual pipeline support")
    print(f"✅ LLM-based pest identification with crop-soil correlation") 
    print(f"✅ MongoDB integration for comprehensive pest database access")
    print(f"✅ Ready for integration with orchestrator and other agents!")
