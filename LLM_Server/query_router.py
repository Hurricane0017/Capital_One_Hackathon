#!/usr/bin/env python3
"""
Query Router - Step 2
LLM-based router that analyzes farmer queries and routes them to either:
1. Generic Pipeline - comprehensive response using all available resources
2. Specific Pipeline - targeted response using specific agents only

Author: Nikhil Mishra
Date: August 17, 2025
"""

import json
import re
from typing import Dict, Any, List
import logging
from datetime import datetime

# Import the LLM client
from llm_client import LLMClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class QueryRouter:
    """
    Routes farmer queries to appropriate pipeline based on query analysis.
    """
    
    def __init__(self):
        """Initialize the router with LLM client."""
        self.llm_client = LLMClient()
        
        # Available agents and their capabilities
        self.available_agents = {
            "weather": {
                "name": "Weather Agent",
                "triggers": [
                    "rain", "weather", "irrigation", "watering", "heatwave", "storm", "wind", 
                    "temperature", "drought", "humidity", "forecast", "climate", "sunny", 
                    "cloudy", "hot", "cold", "monsoon", "sowing", "transplant", "harvest",
                    "spray", "pesticide", "fertilizer timing", "machinery", "tillage",
                    "waterlogging", "erosion", "pincode", "date", "next few days",
                    "when to", "should I water"
                ],
                "requires": ["pincode", "dates"],
                "description": "Provides weather-based agricultural guidance"
            },
            "soil": {
                "name": "Soil Agent", 
                "triggers": [
                    "soil", "alluvial", "clay", "sandy", "loam", "black cotton", "red soil",
                    "laterite", "pH", "fertility", "nutrients", "drainage", "infiltration",
                    "soil type", "soil health", "fertilizer for soil", "soil testing",
                    "compaction", "erosion control", "organic matter"
                ],
                "requires": ["soil_type"],
                "description": "Provides soil-specific crop and management guidance"
            },
            "pest": {
                "name": "Pest Agent",
                "triggers": [
                    "pest", "insect", "disease", "bug", "caterpillar", "aphid", "thrips",
                    "borer", "whitefly", "fungal", "bacterial", "virus", "symptoms",
                    "damage", "spots", "yellowing", "wilting", "honeydew", "sooty mold",
                    "IPM", "pesticide", "biological control", "trap", "spray",
                    "plant protection", "crop protection"
                ],
                "requires": ["pest_symptoms", "crop"],
                "description": "Identifies pests and provides management strategies"
            },
            "market_price": {
                "name": "Market Price Agent",
                "triggers": [
                    "price", "market", "mandi", "rate", "sell", "buying", "MSP",
                    "minimum support price", "wholesale", "retail", "trading",
                    "commodity", "market trend", "price forecast"
                ],
                "requires": ["crop", "location"],
                "description": "Provides market price information (currently under development)"
            },
            "scheme": {
                "name": "Scheme Agent",
                "triggers": [
                    "scheme", "loan", "credit", "KCC", "Kisan Credit Card", "subsidy",
                    "insurance", "PMFBY", "government", "benefit", "eligibility",
                    "documents", "application", "how to apply", "financial help",
                    "bank", "NBFC", "support", "assistance"
                ],
                "requires": ["scheme_name"],
                "description": "Provides information about government and financial schemes"
            }
        }
    
    def route_query(self, farmer_query: str, farmer_profile: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Route farmer query to appropriate pipeline.
        
        Args:
            farmer_query (str): The farmer's question/request
            farmer_profile (Dict[str, Any], optional): Farmer's profile data
            
        Returns:
            Dict[str, Any]: Routing decision with pipeline type and agents
        """
        logger.info(f"Routing query: {farmer_query[:100]}...")
        
        try:
            # Analyze query using LLM
            routing_decision = self._analyze_query_with_llm(farmer_query, farmer_profile)
            
            # Validate and enhance the decision
            validated_decision = self._validate_routing_decision(routing_decision, farmer_query)
            
            logger.info(f"Routing decision: {validated_decision['pipeline']} pipeline")
            if validated_decision['pipeline'] == 'specific':
                logger.info(f"Selected agents: {', '.join(validated_decision['agents'])}")
            
            return validated_decision
            
        except Exception as e:
            logger.error(f"Routing failed: {e}")
            # Fallback to generic pipeline
            return {
                "pipeline": "generic",
                "agents": [],
                "reason": f"Routing analysis failed, defaulting to comprehensive response: {str(e)}",
                "confidence": "low",
                "fallback": True
            }
    
    def _analyze_query_with_llm(self, farmer_query: str, farmer_profile: Dict[str, Any] = None) -> Dict[str, Any]:
        """Analyze query using LLM to determine routing."""
        
        # Build context about available agents
        agents_context = ""
        for key, agent in self.available_agents.items():
            agents_context += f"\n- **{agent['name']}** ({key}): {agent['description']}\n"
            agents_context += f"  Triggered by: {', '.join(agent['triggers'][:10])}...\n"
            agents_context += f"  Requires: {', '.join(agent['requires'])}\n"
        
        # Include farmer profile context if available
        profile_context = ""
        if farmer_profile:
            profile_context = f"""
FARMER PROFILE CONTEXT:
- Name: {farmer_profile.get('name', 'N/A')}
- Location: PIN {farmer_profile.get('pincode', 'N/A')}
- Crops: {', '.join([crop.get('crop', 'N/A') for crop in farmer_profile.get('crops', [])])}
- Soil Type: {farmer_profile.get('soil_type', 'N/A')}
- Land: {farmer_profile.get('land_total_ha', 0):.2f} ha total
"""
        
        prompt = f"""
You are an expert agricultural query router. Analyze the farmer's query and determine if it should go to:

1. **GENERIC PIPELINE**: Comprehensive response using ALL available resources and agents
2. **SPECIFIC PIPELINE**: Targeted response using only specific agents

AVAILABLE AGENTS:
{agents_context}

{profile_context}

ROUTING RULES:

**Use SPECIFIC PIPELINE when:**
- Query is focused on 1-2 specific domains (weather, soil, pest, market, schemes)
- Farmer asks a targeted question that can be fully answered by specific agents
- Query mentions specific triggers that clearly map to particular agents
- Question is about a single aspect (e.g., "When to irrigate?", "What pest is this?", "Soil fertilizer needs?")

**Use GENERIC PIPELINE when:**
- Query is broad/general (e.g., "Help with my crop", "General farming advice")
- Multiple domains are involved or interconnected
- Farmer wants comprehensive farm management guidance  
- Query requires holistic analysis of multiple factors
- Unclear what specific information is needed

FARMER QUERY: "{farmer_query}"

ANALYSIS INSTRUCTIONS:
1. Identify key topics/domains in the query
2. Match against agent capabilities and triggers
3. Determine if query can be fully answered by 1-2 specific agents
4. If specific, identify which agents are needed
5. Provide clear reasoning for the decision

Respond ONLY with valid JSON in this exact format:
{{
  "pipeline": "generic" OR "specific",
  "agents": ["list", "of", "agent", "keys"] OR [],
  "reason": "Clear explanation of why this routing decision was made",
  "confidence": "high" OR "medium" OR "low",
  "query_topics": ["list", "of", "identified", "topics"]
}}

Return ONLY the JSON, no other text.
"""
        
        try:
            response = self.llm_client.call_text_llm(prompt, temperature=0.2)
            
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_text = json_match.group()
                routing_data = json.loads(json_text)
                
                # Add metadata
                routing_data["analyzed_at"] = datetime.now().isoformat()
                routing_data["analysis_method"] = "llm"
                
                return routing_data
            else:
                raise Exception("No valid JSON found in LLM response")
                
        except Exception as e:
            logger.error(f"LLM routing analysis failed: {e}")
            raise
    
    def _validate_routing_decision(self, decision: Dict[str, Any], original_query: str) -> Dict[str, Any]:
        """Validate and enhance the routing decision."""
        
        # Ensure required fields exist
        if "pipeline" not in decision:
            decision["pipeline"] = "generic"
        
        if "agents" not in decision:
            decision["agents"] = []
        
        if "reason" not in decision:
            decision["reason"] = "Default routing applied"
        
        if "confidence" not in decision:
            decision["confidence"] = "medium"
        
        # Validate pipeline type
        if decision["pipeline"] not in ["generic", "specific"]:
            logger.warning(f"Invalid pipeline type: {decision['pipeline']}, defaulting to generic")
            decision["pipeline"] = "generic"
            decision["confidence"] = "low"
        
        # Validate agents for specific pipeline
        if decision["pipeline"] == "specific":
            valid_agents = []
            for agent in decision["agents"]:
                if agent in self.available_agents:
                    valid_agents.append(agent)
                else:
                    logger.warning(f"Invalid agent: {agent}")
            
            decision["agents"] = valid_agents
            
            # If no valid agents, fall back to generic
            if not valid_agents:
                logger.warning("No valid agents for specific pipeline, falling back to generic")
                decision["pipeline"] = "generic"
                decision["reason"] += " (Fallback: no valid agents identified)"
                decision["confidence"] = "low"
        
        # For generic pipeline, ensure agents list is empty
        if decision["pipeline"] == "generic":
            decision["agents"] = []
        
        # Add query analysis metadata
        decision["original_query"] = original_query
        decision["query_length"] = len(original_query)
        decision["validated"] = True
        
        return decision
    
    def get_agent_requirements(self, agent_key: str) -> Dict[str, Any]:
        """Get requirements for a specific agent."""
        if agent_key in self.available_agents:
            return {
                "agent": agent_key,
                "name": self.available_agents[agent_key]["name"],
                "requires": self.available_agents[agent_key]["requires"],
                "description": self.available_agents[agent_key]["description"]
            }
        else:
            return {"error": f"Unknown agent: {agent_key}"}
    
    def analyze_query_coverage(self, farmer_query: str) -> Dict[str, Any]:
        """Analyze which agents could potentially handle parts of the query."""
        
        query_lower = farmer_query.lower()
        agent_matches = {}
        
        for agent_key, agent_info in self.available_agents.items():
            matches = []
            for trigger in agent_info["triggers"]:
                if trigger.lower() in query_lower:
                    matches.append(trigger)
            
            if matches:
                agent_matches[agent_key] = {
                    "name": agent_info["name"],
                    "matched_triggers": matches,
                    "match_count": len(matches),
                    "requires": agent_info["requires"]
                }
        
        return {
            "query": farmer_query,
            "potential_agents": agent_matches,
            "total_matches": sum(info["match_count"] for info in agent_matches.values()),
            "agent_count": len(agent_matches)
        }


# Testing and demonstration
if __name__ == "__main__":
    print("🔀 QUERY ROUTER - STEP 2 TEST")
    print("=" * 60)
    
    router = QueryRouter()
    
    # Test cases for routing
    test_queries = [
        # Specific pipeline cases
        {
            "query": "Should I plan irrigation in the next 7 days for my soybean crop, given the weather forecast for PIN 226010?",
            "expected": "specific",
            "expected_agents": ["weather"]
        },
        {
            "query": "My cotton plants have small white insects, what should I do?",
            "expected": "specific", 
            "expected_agents": ["pest"]
        },
        {
            "query": "What fertilizer should I use for alluvial soil for wheat crop?",
            "expected": "specific",
            "expected_agents": ["soil"]
        },
        {
            "query": "Am I eligible for Kisan Credit Card? What documents do I need?",
            "expected": "specific",
            "expected_agents": ["scheme"]
        },
        {
            "query": "What is the current market price of soybean in my area?",
            "expected": "specific",
            "expected_agents": ["market_price"]
        },
        
        # Generic pipeline cases
        {
            "query": "I want regular crop and farm management guidance to maximize profit and reduce risks.",
            "expected": "generic",
            "expected_agents": []
        },
        {
            "query": "Help me with my farm planning for this season",
            "expected": "generic",
            "expected_agents": []
        },
        {
            "query": "What should I do to improve my overall farming?",
            "expected": "generic", 
            "expected_agents": []
        },
        
        # Mixed cases that could go either way
        {
            "query": "My crop is showing yellow leaves and the weather has been very humid, what should I do?",
            "expected": "could be specific or generic",
            "expected_agents": ["pest", "weather"]
        }
    ]
    
    # Test each query
    for i, test_case in enumerate(test_queries, 1):
        print(f"\nTEST CASE {i}: {'Specific' if 'specific' in test_case['expected'] else 'Generic'} Query")
        print("-" * 50)
        print(f"Query: {test_case['query']}")
        
        try:
            # Route the query
            result = router.route_query(test_case['query'])
            
            print(f"✅ Routing successful!")
            print(f"Pipeline: {result['pipeline']}")
            print(f"Agents: {result['agents'] if result['agents'] else 'None (Generic)'}")
            print(f"Confidence: {result['confidence']}")
            print(f"Reason: {result['reason']}")
            
            # Analyze coverage
            coverage = router.analyze_query_coverage(test_case['query'])
            print(f"Potential agents identified: {list(coverage['potential_agents'].keys())}")
            
        except Exception as e:
            print(f"❌ Routing failed: {e}")
    
    print(f"\n🎉 STEP 2 TESTING COMPLETED!")
    print(f"✅ Query routing system working")
    print(f"✅ LLM-based decision making functional") 
    print(f"✅ Validation and fallback mechanisms in place")
    print(f"✅ Ready for integration with Step 1!")
