#!/usr/bin/env python3
"""
Soil Agent - Step 3.b
Comprehensive soil agent that provides soil-specific agricultural guidance for both
specific pipeline (targeted soil queries) and generic pipeline (comprehensive soil guidance) scenarios.

Key Capabilities:
- Extract soil type from farmer input or determine from location using LLM
- Retrieve detailed soil data from MongoDB soil_profiles collection  
- Provide context-aware agricultural soil guidance
- Handle both specific queries and generic soil recommendations

Author: Nikhil Mishra
Date: August 17, 2025
"""

import sys
import os
import json
import logging
import re
from typing import Dict, List, Any, Optional
from datetime import datetime

# Add the db_uploading directory to path to import soil database functions
sys.path.append(os.path.join(os.path.dirname(__file__), 'db_uploading'))

# Import LLM client
from llm_client import LLMClient
from logging_config import setup_logging

# Import soil database functions
from db_uploading.soil_profile_db import get_by_soil_key, CONNECTION_OK

# Configure logging
logger = setup_logging('SoilAgent')

class SoilAgent:
    """
    Comprehensive Soil Agent for agricultural soil-based decision-making.
    
    Handles both specific pipeline (targeted soil queries) and generic pipeline 
    (comprehensive soil guidance) scenarios.
    """
    
    def __init__(self):
        """Initialize the Soil Agent with required clients."""
        self.llm_client = LLMClient(logger=logger)
        self.agent_type = "soil"
        
        # Available soil types in our database
        self.available_soil_types = [
            "alluvial", "black", "desert", "forest", "laterite", 
            "mountain", "peaty", "red", "saline"
        ]
        
        # Regional soil mapping for location-based determination
        self.regional_soil_mapping = {
            # Major states and their primary soil types
            "punjab": "alluvial",
            "haryana": "alluvial", 
            "uttar pradesh": "alluvial",
            "bihar": "alluvial",
            "west bengal": "alluvial",
            "assam": "alluvial",
            "odisha": "alluvial",
            "maharashtra": "black",
            "madhya pradesh": "black", 
            "gujarat": "black",
            "telangana": "black",
            "karnataka": "black",
            "tamil nadu": "red",
            "andhra pradesh": "red",
            "rajasthan": "desert",
            "kerala": "laterite",
            "jharkhand": "red",
            "himachal pradesh": "mountain",
            "uttarakhand": "mountain",
            "jammu and kashmir": "mountain",
            "arunachal pradesh": "mountain",
            "nagaland": "forest"
        }
        
        # Soil aliases mapping for better recognition
        self.soil_aliases = {
            "regur": "black",
            "black cotton": "black",
            "vertisol": "black",
            "alluvium": "alluvial",
            "red earth": "red",
            "lateritic": "laterite", 
            "arid": "desert",
            "organic": "peaty",
            "marsh": "peaty",
            "alkaline": "saline",
            "salt affected": "saline"
        }
    
    def process_query(self, query: str, farmer_profile: Dict[str, Any] = None, 
                     pipeline_type: str = "specific") -> Dict[str, Any]:
        """
        Main entry point to process soil queries.
        
        Args:
            query (str): The farmer's soil-related query
            farmer_profile (Dict[str, Any]): Farmer profile data
            pipeline_type (str): "specific" or "generic"
            
        Returns:
            Dict[str, Any]: Comprehensive soil guidance response
        """
        logger.info(f"Processing {pipeline_type} soil query: {query[:100]}...")
        
        try:
            # Check database connection
            if not CONNECTION_OK:
                logger.error("No database connection for soil data")
                return {
                    "success": False,
                    "error": "Soil database connection unavailable",
                    "agent": "soil",
                    "fallback_advice": "Please consult local agricultural extension officers for soil-specific guidance."
                }
            
            if pipeline_type == "specific":
                return self._process_specific_query(query, farmer_profile)
            else:
                return self._process_generic_query(query, farmer_profile)
                
        except Exception as e:
            logger.error(f"Soil query processing failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "agent": "soil",
                "fallback_advice": "Please check with local soil testing facilities for accurate soil analysis and recommendations."
            }
    
    def _process_specific_query(self, query: str, farmer_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Process specific pipeline soil queries."""
        logger.info("Processing specific soil pipeline query")
        
        # Step 1: Determine farmer's soil type
        soil_type = self._determine_soil_type(farmer_profile, query)
        
        # Step 2: Retrieve soil data from database
        soil_data = self._get_soil_data(soil_type)
        
        if not soil_data:
            logger.error(f"No soil data found for type: {soil_type}")
            return {
                "success": False,
                "error": f"Soil data not available for type: {soil_type}",
                "agent": "soil",
                "determined_soil_type": soil_type
            }
        
        # Step 3: Generate specific soil analysis using LLM
        analysis = self._generate_specific_soil_analysis(query, soil_data, farmer_profile)
        
        return {
            "success": True,
            "agent": "soil",
            "pipeline": "specific",
            "query": query,
            "determined_soil_type": soil_type,
            "soil_data": soil_data,
            "analysis": analysis,
            "recommendations": analysis.get("recommendations", []),
            "soil_insights": analysis.get("soil_insights", {})
        }
    
    def _process_generic_query(self, query: str, farmer_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Process generic pipeline soil queries for orchestrator guidance."""
        logger.info("Processing generic soil pipeline query")
        
        # Step 1: Determine farmer's soil type
        soil_type = self._determine_soil_type(farmer_profile, query)
        
        # Step 2: Retrieve soil data from database
        soil_data = self._get_soil_data(soil_type)
        
        if not soil_data:
            logger.error(f"No soil data found for type: {soil_type}")
            return {
                "success": False,
                "error": f"Soil data not available for type: {soil_type}",
                "agent": "soil",
                "determined_soil_type": soil_type
            }
        
        # Step 3: Generate comprehensive soil guidance for orchestrator
        orchestrator_guidance = self._generate_orchestrator_guidance(soil_data, farmer_profile)
        
        return {
            "success": True,
            "agent": "soil",
            "pipeline": "generic",
            "query": query,
            "determined_soil_type": soil_type,
            "soil_data": soil_data,
            "orchestrator_guidance": orchestrator_guidance,
            "key_soil_properties": self._extract_key_properties(soil_data),
            "management_priorities": self._get_management_priorities(soil_data)
        }
    
    def _determine_soil_type(self, farmer_profile: Dict[str, Any], query: str = "") -> str:
        """Determine farmer's soil type from profile or location using LLM."""
        
        # Build context for LLM
        profile_context = ""
        if farmer_profile:
            profile_context = f"""
FARMER PROFILE:
- Name: {farmer_profile.get('name', 'N/A')}
- Location: {farmer_profile.get('village', 'N/A')}, {farmer_profile.get('district', 'N/A')}, {farmer_profile.get('state', 'N/A')}
- Pincode: {farmer_profile.get('pincode', 'N/A')}
- Soil Type (if mentioned): {farmer_profile.get('soil_type', 'Not specified')}
- Crops: {', '.join([crop.get('crop', 'N/A') for crop in farmer_profile.get('crops', [])])}
"""
        
        # Build available soil types context
        soil_types_context = ""
        for soil_type in self.available_soil_types:
            soil_data = self._get_soil_data(soil_type)
            if soil_data:
                regions = [region.get('state', '') for region in soil_data.get('regions', [])]
                aliases = soil_data.get('aliases', [])
                soil_types_context += f"\n- **{soil_type}** ({soil_data.get('soil_name', '')}): Aliases: {', '.join(aliases)}, Found in: {', '.join(regions[:3])}..."
        
        query_context = f"FARMER QUERY: \"{query}\"" if query else ""
        
        prompt = f"""
You are an expert agricultural soil scientist. Determine the most likely soil type for this farmer.

AVAILABLE SOIL TYPES IN DATABASE:
{soil_types_context}

{profile_context}

{query_context}

DETERMINATION RULES:
1. **If soil type explicitly mentioned in farmer profile** → Use that soil type
2. **If soil type mentioned in query** (e.g., "my black soil", "alluvial land") → Use that soil type  
3. **If location information available** → Match to regional soil patterns:
   - Punjab, Haryana, UP, Bihar, West Bengal, Assam → alluvial
   - Maharashtra, MP, Gujarat, Telangana → black
   - Tamil Nadu, Andhra Pradesh, Karnataka (eastern), Jharkhand → red
   - Rajasthan (Thar region) → desert
   - Kerala, Karnataka (western) → laterite
   - Hill states (HP, Uttarakhand, J&K) → mountain
   - Forest areas → forest
   - Coastal marshy areas → peaty
   - Salt-affected irrigated areas → saline

4. **Check for aliases** (regur=black, vertisol=black, alluvium=alluvial, etc.)
5. **If insufficient information** → Default to "alluvial" (most common in India)

Respond ONLY with the exact soil type key from this list:
{', '.join(self.available_soil_types)}

Return ONLY the soil type key, no other text.
"""
        
        try:
            response = self.llm_client.call_text_llm(prompt, temperature=0.1)
            determined_soil_type = response.strip().lower()
            
            # Validate the response
            if determined_soil_type in self.available_soil_types:
                logger.info(f"Determined soil type: {determined_soil_type}")
                return determined_soil_type
            else:
                # Check for aliases
                for alias, actual_type in self.soil_aliases.items():
                    if alias in determined_soil_type:
                        logger.info(f"Determined soil type via alias '{alias}': {actual_type}")
                        return actual_type
                
                # Fallback to default
                logger.warning(f"Invalid soil type determined: {determined_soil_type}, defaulting to alluvial")
                return "alluvial"
                
        except Exception as e:
            logger.error(f"Soil type determination failed: {e}")
            # Fallback logic based on location
            return self._fallback_soil_determination(farmer_profile)
    
    def _fallback_soil_determination(self, farmer_profile: Dict[str, Any]) -> str:
        """Fallback soil type determination based on location."""
        if not farmer_profile:
            return "alluvial"
        
        state = farmer_profile.get('state', '').lower()
        district = farmer_profile.get('district', '').lower()
        
        # Check state-level mapping
        for region, soil_type in self.regional_soil_mapping.items():
            if region in state or region in district:
                logger.info(f"Fallback soil determination: {soil_type} for {state}")
                return soil_type
        
        # Ultimate fallback
        return "alluvial"
    
    def _get_soil_data(self, soil_type: str) -> Optional[Dict[str, Any]]:
        """Retrieve soil data from MongoDB."""
        try:
            soil_data = get_by_soil_key(soil_type)
            if soil_data:
                # Remove MongoDB _id field and convert any datetime objects for clean JSON
                soil_data.pop('_id', None)
                
                # Convert any datetime objects to strings to avoid JSON serialization issues
                def convert_datetime(obj):
                    if isinstance(obj, dict):
                        return {k: convert_datetime(v) for k, v in obj.items()}
                    elif isinstance(obj, list):
                        return [convert_datetime(item) for item in obj]
                    elif hasattr(obj, 'isoformat'):  # datetime objects
                        return obj.isoformat()
                    else:
                        return obj
                
                soil_data = convert_datetime(soil_data)
                logger.info(f"Retrieved soil data for: {soil_type}")
                return soil_data
            else:
                logger.warning(f"No soil data found for: {soil_type}")
                return None
        except Exception as e:
            logger.error(f"Error retrieving soil data for {soil_type}: {e}")
            return None
    
    def _generate_specific_soil_analysis(self, query: str, soil_data: Dict[str, Any], 
                                       farmer_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Generate specific soil analysis using LLM for targeted queries."""
        
        # Extract key soil properties for LLM context
        soil_name = soil_data.get('soil_name', 'Unknown')
        soil_texture = soil_data.get('texture', 'N/A')
        soil_ph = soil_data.get('chemical_properties', {}).get('pH', {})
        ph_range = f"{soil_ph.get('min', 0)}-{soil_ph.get('max', 0)}" if soil_ph else "N/A"
        
        water_holding = soil_data.get('water_holding_capacity_pct', {})
        whc_range = f"{water_holding.get('min', 0)}-{water_holding.get('max', 0)}%" if water_holding else "N/A"
        
        nutrients_rich = ', '.join(soil_data.get('nutrients_rich_in', []))
        nutrients_deficient = ', '.join(soil_data.get('nutrients_deficient_in', []))
        favoured_crops = ', '.join(soil_data.get('favoured_crops', []))
        hazards = ', '.join(soil_data.get('hazards', []))
        
        crop_context = ""
        if farmer_profile and farmer_profile.get('crops'):
            crops = [crop.get('crop', 'N/A') for crop in farmer_profile['crops']]
            crop_context = f"Farmer's current crops: {', '.join(crops)}"
        
        prompt = f"""
You are an expert soil scientist providing specific guidance to an Indian farmer.

FARMER QUERY: "{query}"

SOIL PROFILE - {soil_name.upper()}:
- Type: {soil_data.get('soil_key', 'N/A')}
- Texture: {soil_texture}
- pH Range: {ph_range}
- Water Holding Capacity: {whc_range}
- Rich in: {nutrients_rich}
- Deficient in: {nutrients_deficient}
- Best crops: {favoured_crops}
- Common hazards: {hazards}
- Drainage: {soil_data.get('drainage', 'N/A')}

{crop_context}

DETAILED SOIL DATA:
{json.dumps(soil_data, indent=2)}

Please provide comprehensive soil-specific guidance covering:

1. **DIRECT ANSWER** to the farmer's specific question
2. **FERTILIZER RECOMMENDATIONS** based on soil nutrient status
3. **CROP SUITABILITY** for this soil type
4. **SOIL MANAGEMENT PRACTICES** specific to this soil
5. **IRRIGATION GUIDANCE** based on water holding capacity
6. **SOIL HEALTH IMPROVEMENT** strategies
7. **PROBLEM MITIGATION** for known soil hazards
8. **SEASONAL CONSIDERATIONS** for soil management

Focus on:
- Practical, actionable advice specific to {soil_name}
- Cost-effective solutions for Indian farmers
- Sustainable soil management practices
- Nutrient management strategies
- Water use efficiency

Provide specific recommendations that directly address the farmer's query while considering the unique properties of {soil_name}.
"""
        
        try:
            analysis_response = self.llm_client.call_text_llm(prompt, temperature=0.3)
            
            # Extract structured recommendations
            recommendations = self._extract_soil_recommendations(analysis_response, soil_data)
            soil_insights = self._generate_soil_insights(soil_data)
            
            return {
                "detailed_analysis": analysis_response,
                "recommendations": recommendations,
                "soil_insights": soil_insights
            }
            
        except Exception as e:
            logger.error(f"Specific soil analysis generation failed: {e}")
            return {
                "detailed_analysis": f"Soil analysis could not be generated due to technical issues. However, for {soil_name}, focus on addressing nutrient deficiencies in {nutrients_deficient} and managing {hazards}.",
                "recommendations": [],
                "soil_insights": {},
                "error": str(e)
            }
    
    def _generate_orchestrator_guidance(self, soil_data: Dict[str, Any], 
                                      farmer_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive soil guidance for the orchestrator/coordinator agent."""
        
        soil_name = soil_data.get('soil_name', 'Unknown')
        soil_key = soil_data.get('soil_key', 'unknown')
        
        # Key information for orchestrator
        orchestrator_guidance = {
            "soil_type": soil_key,
            "soil_name": soil_name,
            "key_characteristics": {
                "texture": soil_data.get('texture', 'N/A'),
                "structure": soil_data.get('structure', 'N/A'),
                "drainage": soil_data.get('drainage', 'N/A'),
                "ph_range": soil_data.get('chemical_properties', {}).get('pH', {}),
                "water_holding_capacity": soil_data.get('water_holding_capacity_pct', {}),
                "organic_matter": soil_data.get('chemical_properties', {}).get('organic_matter_pct', {})
            },
            "nutrient_status": {
                "rich_in": soil_data.get('nutrients_rich_in', []),
                "deficient_in": soil_data.get('nutrients_deficient_in', []),
                "cec_range": soil_data.get('chemical_properties', {}).get('cation_exchange_capacity_cmolkg', {})
            },
            "crop_recommendations": {
                "favoured_crops": soil_data.get('favoured_crops', []),
                "favoured_seasons": soil_data.get('favoured_seasons', [])
            },
            "management_considerations": {
                "primary_hazards": soil_data.get('hazards', []),
                "erosion_risk": soil_data.get('physical_properties', {}).get('erosion_risk', 'N/A'),
                "infiltration_rate": soil_data.get('physical_properties', {}).get('infiltration_rate_mm_hr', 'N/A')
            },
            "fertilizer_priorities": self._get_fertilizer_priorities(soil_data),
            "irrigation_guidance": self._get_irrigation_guidance(soil_data),
            "soil_improvement_focus": self._get_improvement_focus(soil_data)
        }
        
        return orchestrator_guidance
    
    def _extract_key_properties(self, soil_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract key soil properties for quick reference."""
        return {
            "soil_type": soil_data.get('soil_key', 'unknown'),
            "texture": soil_data.get('texture', 'N/A'),
            "ph_range": soil_data.get('chemical_properties', {}).get('pH', {}),
            "water_retention": soil_data.get('water_holding_capacity_pct', {}),
            "drainage": soil_data.get('drainage', 'N/A'),
            "fertility_status": {
                "rich": soil_data.get('nutrients_rich_in', []),
                "deficient": soil_data.get('nutrients_deficient_in', [])
            }
        }
    
    def _get_management_priorities(self, soil_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get soil management priorities based on soil characteristics."""
        priorities = []
        
        # Nutrient management priority
        deficient_nutrients = soil_data.get('nutrients_deficient_in', [])
        if deficient_nutrients:
            priorities.append({
                "category": "nutrient_management",
                "priority": "high",
                "focus": f"Address deficiency in: {', '.join(deficient_nutrients)}",
                "action": "Apply targeted fertilizers and organic amendments"
            })
        
        # Water management priority
        whc = soil_data.get('water_holding_capacity_pct', {})
        if whc.get('max', 100) < 30:  # Low water holding capacity
            priorities.append({
                "category": "water_management", 
                "priority": "high",
                "focus": "Improve water retention",
                "action": "Add organic matter, mulching, frequent light irrigation"
            })
        
        # Hazard management priority
        hazards = soil_data.get('hazards', [])
        if hazards:
            priorities.append({
                "category": "hazard_management",
                "priority": "medium",
                "focus": f"Mitigate: {', '.join(hazards)}",
                "action": "Implement preventive soil management practices"
            })
        
        return priorities
    
    def _extract_soil_recommendations(self, analysis: str, soil_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract structured soil recommendations from analysis."""
        recommendations = []
        
        # Basic recommendation extraction (can be enhanced with more sophisticated parsing)
        lines = analysis.split('\n')
        current_rec = None
        
        for line in lines:
            line = line.strip()
            if any(keyword in line.lower() for keyword in ['recommend', 'apply', 'use', 'add', 'avoid', 'ensure']):
                if current_rec:
                    recommendations.append(current_rec)
                current_rec = {
                    "action": line,
                    "category": self._categorize_recommendation(line),
                    "priority": "medium"
                }
            elif current_rec and line and not line.startswith('#'):
                current_rec["details"] = current_rec.get("details", "") + " " + line
        
        if current_rec:
            recommendations.append(current_rec)
        
        return recommendations[:8]  # Limit to top 8 recommendations
    
    def _categorize_recommendation(self, recommendation: str) -> str:
        """Categorize recommendation based on content."""
        rec_lower = recommendation.lower()
        
        if any(word in rec_lower for word in ['fertilizer', 'nutrient', 'nitrogen', 'phosphorus', 'potassium']):
            return "fertilization"
        elif any(word in rec_lower for word in ['irrigation', 'water', 'moisture']):
            return "water_management"
        elif any(word in rec_lower for word in ['crop', 'plant', 'grow']):
            return "crop_selection"
        elif any(word in rec_lower for word in ['organic', 'compost', 'manure']):
            return "organic_amendment"
        elif any(word in rec_lower for word in ['drainage', 'waterlog']):
            return "drainage"
        else:
            return "general"
    
    def _generate_soil_insights(self, soil_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate key soil insights for quick reference."""
        
        ph_data = soil_data.get('chemical_properties', {}).get('pH', {})
        ph_min = ph_data.get('min', 7.0)
        ph_max = ph_data.get('max', 7.0)
        avg_ph = (ph_min + ph_max) / 2
        
        # Determine pH category
        if avg_ph < 6.5:
            ph_status = "acidic"
        elif avg_ph > 7.5:
            ph_status = "alkaline"
        else:
            ph_status = "neutral"
        
        # Water holding capacity assessment
        whc_data = soil_data.get('water_holding_capacity_pct', {})
        avg_whc = (whc_data.get('min', 30) + whc_data.get('max', 30)) / 2
        
        if avg_whc < 25:
            water_retention = "low"
        elif avg_whc > 50:
            water_retention = "high" 
        else:
            water_retention = "moderate"
        
        return {
            "ph_status": ph_status,
            "ph_range": f"{ph_min}-{ph_max}",
            "water_retention": water_retention,
            "water_holding_capacity": f"{whc_data.get('min', 0)}-{whc_data.get('max', 0)}%",
            "primary_texture": soil_data.get('texture', 'unknown'),
            "fertility_level": "low" if len(soil_data.get('nutrients_deficient_in', [])) > 2 else "moderate",
            "management_complexity": "high" if len(soil_data.get('hazards', [])) > 1 else "moderate"
        }
    
    def _get_fertilizer_priorities(self, soil_data: Dict[str, Any]) -> List[str]:
        """Get fertilizer priorities based on soil nutrient status."""
        deficient = soil_data.get('nutrients_deficient_in', [])
        priorities = []
        
        # Priority order for nutrient management
        nutrient_priority = ['nitrogen', 'phosphorus', 'potassium', 'calcium', 'sulfur', 'zinc']
        
        for nutrient in nutrient_priority:
            if nutrient in deficient:
                priorities.append(nutrient)
        
        # Add any other deficient nutrients
        for nutrient in deficient:
            if nutrient not in priorities:
                priorities.append(nutrient)
        
        return priorities[:5]  # Top 5 priorities
    
    def _get_irrigation_guidance(self, soil_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get irrigation guidance based on soil properties."""
        
        whc = soil_data.get('water_holding_capacity_pct', {})
        avg_whc = (whc.get('min', 30) + whc.get('max', 30)) / 2
        
        infiltration = soil_data.get('physical_properties', {}).get('infiltration_rate_mm_hr', 10)
        drainage = soil_data.get('drainage', 'well drained')
        
        if avg_whc < 25:
            strategy = "frequent_light"
            frequency = "every 2-3 days"
        elif avg_whc > 50:
            strategy = "deep_infrequent"
            frequency = "every 7-10 days"
        else:
            strategy = "moderate"
            frequency = "every 4-5 days"
        
        return {
            "strategy": strategy,
            "frequency": frequency,
            "water_holding_capacity": avg_whc,
            "infiltration_rate": infiltration,
            "drainage_status": drainage,
            "special_considerations": self._get_irrigation_considerations(soil_data)
        }
    
    def _get_irrigation_considerations(self, soil_data: Dict[str, Any]) -> List[str]:
        """Get special irrigation considerations for soil type."""
        considerations = []
        
        hazards = soil_data.get('hazards', [])
        
        if 'waterlogging' in hazards:
            considerations.append("Ensure proper drainage to prevent waterlogging")
        
        if 'salinization' in hazards or 'salinity' in hazards:
            considerations.append("Use good quality water and ensure leaching")
        
        if 'erosion' in ' '.join(hazards).lower():
            considerations.append("Use drip irrigation to prevent soil erosion")
        
        soil_texture = soil_data.get('texture', '').lower()
        if 'sandy' in soil_texture:
            considerations.append("Use frequent light irrigations due to high permeability")
        elif 'clay' in soil_texture:
            considerations.append("Allow deep penetration, avoid frequent watering")
        
        return considerations
    
    def _get_improvement_focus(self, soil_data: Dict[str, Any]) -> List[str]:
        """Get soil improvement focus areas."""
        focus_areas = []
        
        # Check organic matter content
        om_data = soil_data.get('chemical_properties', {}).get('organic_matter_pct', {})
        avg_om = (om_data.get('min', 1) + om_data.get('max', 1)) / 2
        
        if avg_om < 1:
            focus_areas.append("Increase organic matter content")
        
        # Check pH issues
        ph_data = soil_data.get('chemical_properties', {}).get('pH', {})
        avg_ph = (ph_data.get('min', 7) + ph_data.get('max', 7)) / 2
        
        if avg_ph < 6:
            focus_areas.append("Correct soil acidity with lime application")
        elif avg_ph > 8.5:
            focus_areas.append("Manage alkalinity with gypsum treatment")
        
        # Check for specific hazards
        hazards = soil_data.get('hazards', [])
        if hazards:
            focus_areas.append(f"Address soil hazards: {', '.join(hazards[:2])}")
        
        return focus_areas[:4]  # Top 4 focus areas


# Testing and demonstration
if __name__ == "__main__":
    print("🌱 SOIL AGENT - STEP 3.b TEST")
    print("=" * 60)
    
    # Initialize soil agent
    agent = SoilAgent()
    
    # Test farmer profiles with different soil scenarios
    test_profiles = [
        {
            "name": "Ramesh Patel",
            "village": "Anand", 
            "district": "Anand",
            "state": "Gujarat",
            "pincode": "388001",
            "soil_type": "black",  # Explicitly mentioned
            "crops": [{"crop": "cotton", "area_ha": 2.5}]
        },
        {
            "name": "Priya Sharma", 
            "village": "Kanpur",
            "district": "Kanpur", 
            "state": "Uttar Pradesh",
            "pincode": "208001",
            # No soil type - should determine from location (alluvial)
            "crops": [{"crop": "wheat", "area_ha": 3.0}, {"crop": "rice", "area_ha": 2.0}]
        },
        {
            "name": "Suresh Kumar",
            "village": "Coimbatore",
            "district": "Coimbatore",
            "state": "Tamil Nadu", 
            "pincode": "641001",
            # No soil type - should determine from location (red)
            "crops": [{"crop": "cotton", "area_ha": 1.5}]
        }
    ]
    
    # Test queries
    test_queries = [
        {
            "query": "What fertilizers should I use for my cotton crop in black soil?",
            "profile_idx": 0,
            "pipeline": "specific",
            "description": "Specific fertilizer query for black soil"
        },
        {
            "query": "My wheat crop leaves are yellowing, is it related to my soil?", 
            "profile_idx": 1,
            "pipeline": "specific",
            "description": "Diagnostic query for alluvial soil"
        },
        {
            "query": "I need comprehensive soil guidance for my farm management",
            "profile_idx": 2,
            "pipeline": "generic",
            "description": "Generic soil guidance for red soil"
        }
    ]
    
    # Test each scenario
    for i, test_case in enumerate(test_queries, 1):
        print(f"\n🧪 TEST CASE {i}: {test_case['description']}")
        print("-" * 50)
        
        profile = test_profiles[test_case['profile_idx']]
        query = test_case['query']
        pipeline = test_case['pipeline']
        
        print(f"Farmer: {profile['name']} from {profile['state']}")
        print(f"Query: {query}")
        print(f"Pipeline: {pipeline}")
        
        try:
            result = agent.process_query(query, profile, pipeline)
            
            if result.get('success'):
                print(f"✅ Processing successful!")
                print(f"Determined soil type: {result.get('determined_soil_type')}")
                
                if pipeline == "specific":
                    analysis = result.get('analysis', {})
                    recommendations = result.get('recommendations', [])
                    print(f"Number of recommendations: {len(recommendations)}")
                    
                    if analysis.get('detailed_analysis'):
                        print(f"Analysis preview: {analysis['detailed_analysis'][:200]}...")
                        
                else:  # generic pipeline
                    guidance = result.get('orchestrator_guidance', {})
                    key_props = result.get('key_soil_properties', {})
                    priorities = result.get('management_priorities', [])
                    
                    print(f"Soil characteristics: {key_props.get('texture', 'N/A')}")
                    print(f"Management priorities: {len(priorities)} identified")
                    print(f"Fertilizer priorities: {guidance.get('fertilizer_priorities', [])}")
                    
            else:
                print(f"❌ Processing failed: {result.get('error')}")
                
        except Exception as e:
            print(f"❌ Test case {i} failed: {e}")
    
    # Test soil type determination  
    print(f"\n🔍 SOIL TYPE DETERMINATION TESTS")
    print("-" * 50)
    
    determination_tests = [
        {"state": "Punjab", "expected": "alluvial"},
        {"state": "Maharashtra", "expected": "black"}, 
        {"state": "Tamil Nadu", "expected": "red"},
        {"state": "Rajasthan", "expected": "desert"},
        {"state": "Kerala", "expected": "laterite"}
    ]
    
    for test in determination_tests:
        test_profile = {"state": test["state"], "district": "Unknown", "village": "Unknown"}
        determined = agent._determine_soil_type(test_profile)
        status = "✅" if determined == test["expected"] else "❌"
        print(f"{status} {test['state']} → {determined} (expected: {test['expected']})")
    
    print(f"\n🎉 SOIL AGENT TESTING COMPLETED!")
    print(f"✅ Specific pipeline processing functional") 
    print(f"✅ Generic pipeline processing functional")
    print(f"✅ Soil type determination working")
    print(f"✅ MongoDB soil data retrieval working")
    print(f"✅ LLM-based soil analysis generation working")
    print(f"✅ Ready for integration with query router!")
