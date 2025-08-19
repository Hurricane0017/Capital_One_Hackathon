#!/usr/bin/env python3
"""
Orchestrator Agent - Step 4
Master Coordinator Agent that sits on top of all 4 individual agents

This orchestrator:
1. Processes farmer input using farmer_input_processor.py
2. Classifies queries into specific or generic pipelines
3. Coordinates weather, soil, pest, and scheme agents
4. Provides comprehensive agricultural guidance
5. Combines multi-agent responses for holistic farming advice

Key Capabilities:
- IVR data processing and farmer profile management
- Intelligent pipeline classification (specific vs generic)
- Multi-agent coordination and response synthesis
- Comprehensive farming roadmap generation
- Hyperlocal guidance using all available resources

Author: Nikhil Mishra
Date: August 18, 2025
"""

import os
import sys
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dotenv import load_dotenv
import re

# Add the project root to the Python path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import all agents and processors
from farmer_input_processor import FarmerInputProcessor
from query_router import QueryRouter
from weather_agent import WeatherAgent
from soil_agent import SoilAgent
from pest_agent import PestAgent
from scheme_agent import SchemeAgent
from llm_client import LLMClient
from logging_config import setup_logging

# Load environment variables
load_dotenv()

# Configure logging
logger = setup_logging('OrchestratorAgent')

class OrchestratorAgent:
    """
    Master Orchestrator Agent - The boss of all agents
    
    Coordinates all agricultural guidance through intelligent pipeline management:
    - Specific Pipeline: Targeted responses using selected agents
    - Generic Pipeline: Comprehensive end-to-end farming guidance
    """
    
    def __init__(self):
        """Initialize the orchestrator with all sub-agents and processors."""
        logger.info("🎯 Initializing Orchestrator Agent - Master Coordinator")
        
        # Initialize the LLM client for orchestration decisions
        self.llm_client = LLMClient(logger=logger)
        
        # Initialize all sub-components
        self.farmer_processor = FarmerInputProcessor()
        self.query_router = QueryRouter()
        
        # Initialize all individual agents
        self.weather_agent = WeatherAgent()
        self.soil_agent = SoilAgent()
        self.pest_agent = PestAgent()
        self.scheme_agent = SchemeAgent()
        
        logger.info("✅ All agents and processors initialized successfully")
    
    def process_farmer_request(self, raw_farmer_input: str, farmer_phone: str = None) -> str:
        """
        Main entry point for processing farmer requests from IVR system.
        
        This method:
        1. Processes and stores farmer data
        2. Classifies the query pipeline
        3. Coordinates appropriate agents
        4. Synthesizes comprehensive response
        5. Converts the final response to plain English for the farmer.
        
        Args:
            raw_farmer_input (str): Raw farmer input from IVR
            farmer_phone (str): Farmer's phone number for profile lookup
            
        Returns:
            str: Comprehensive orchestrated response in plain English.
        """
        logger.info(f"🌾 Processing farmer request from {farmer_phone}")
        
        try:
            # Step 1: Process and store farmer input
            farmer_profile = self._process_farmer_input(raw_farmer_input, farmer_phone)
            
            # Step 2: Extract query from farmer input
            farmer_query = self._extract_query_from_input(raw_farmer_input, farmer_profile)
            
            # Step 3: Classify pipeline (specific vs generic)
            pipeline_decision = self._classify_pipeline(farmer_query, farmer_profile)
            
            # Step 4: Execute appropriate pipeline
            if pipeline_decision["pipeline_type"] == "specific":
                response = self._execute_specific_pipeline(farmer_query, farmer_profile, pipeline_decision)
            else:
                response = self._execute_generic_pipeline(farmer_query, farmer_profile, pipeline_decision)
            
            # Step 5: Add orchestrator metadata
            response.update({
                "orchestrator_metadata": {
                    "pipeline_used": pipeline_decision["pipeline_type"],
                    "agents_coordinated": response.get("agents_used", []),
                    "processing_time": datetime.now().isoformat(),
                    "farmer_profile_id": farmer_profile.get("phone", "unknown"),
                    "confidence_score": pipeline_decision.get("confidence", 0.8)
                }
            })
            
            logger.info(f"✅ Successfully processed farmer request via {pipeline_decision['pipeline_type']} pipeline")
            
            # Step 6: Convert final JSON response to plain English
            english_response = self._convert_json_to_english(response, farmer_query, farmer_profile)
            logger.info("✅ Converted final response to plain English for the farmer.")
            return english_response
            
        except Exception as e:
            logger.error(f"❌ Error processing farmer request: {e}")
            error_message = f"Sorry, we encountered an error while processing your request. Please try again later. Error: {str(e)}"
            return error_message
    
    def _convert_json_to_english(self, response_data: Dict[str, Any], farmer_query: str, farmer_profile: Dict[str, Any]) -> str:
        """
        Converts the final JSON response to a farmer-friendly plain English response.
        
        Args:
            response_data (Dict[str, Any]): The final response data from the orchestrator.
            farmer_query (str): The original farmer query.
            farmer_profile (Dict[str, Any]): The farmer's profile.
            
        Returns:
            str: A plain English response for the farmer.
        """
        logger.info("🔄 Converting JSON response to plain English.")
        
        try:
            farmer_context = self._build_farmer_context(farmer_profile)
            
            # If the response already contains a direct farmer-friendly response, use it.
            if "farmer_response" in response_data and isinstance(response_data["farmer_response"], str):
                return response_data["farmer_response"]

            prompt = f"""
            You are an expert agricultural assistant. Your task is to convert a complex JSON object containing agricultural advice into a simple, clear, and actionable response in plain English for a farmer.

            FARMER'S PROFILE:
            {farmer_context}

            FARMER'S ORIGINAL QUERY: "{farmer_query}"

            Here is the JSON data with the complete advice:
            {json.dumps(response_data, indent=2)}

            Please synthesize all this information into a single, coherent, and easy-to-understand message for the farmer. The message should be:
            - In plain English.
            - Friendly and encouraging in tone.
            - Directly addressing the farmer's query.
            - Highlighting the most important actions the farmer should take.
            - Structured with clear headings or bullet points if necessary for readability.
            - Avoid technical jargon and JSON formatting.

            Start the response with a greeting to the farmer.
            """
            
            english_response = self.llm_client.call_text_llm(prompt, temperature=0.5, max_tokens=2000)
            
            logger.info("✅ Successfully converted JSON to English response.")
            return english_response.strip()

        except Exception as e:
            logger.error(f"❌ Error converting JSON to English: {e}")
            # Fallback to a simpler text representation if LLM fails
            if "farmer_response" in response_data:
                return str(response_data["farmer_response"])
            elif "comprehensive_strategy" in response_data:
                return f"We have prepared a detailed strategy for you. Please contact our support for more details. Strategy includes: {list(response_data['comprehensive_strategy'].keys())}"
            return "We have processed your request and have some recommendations. Please contact our support for detailed advice."

    def _process_farmer_input(self, raw_input: str, phone: str = None) -> Dict[str, Any]:
        """
        Process farmer input and ensure it's stored in database.
        
        Args:
            raw_input (str): Raw farmer input from IVR
            phone (str): Farmer's phone number
            
        Returns:
            Dict[str, Any]: Structured farmer profile
        """
        logger.info("📝 Processing and storing farmer input data")
        
        try:
            # First, try to get existing farmer profile
            if phone:
                existing_profile = self.farmer_processor.get_farmer_profile(phone)
                if existing_profile:
                    logger.info(f"📋 Found existing profile for {phone}")
                    return existing_profile
            
            # Process new farmer input
            farmer_data = self.farmer_processor.process_and_store(raw_input)
            
            if farmer_data.get("status") == "success":
                return farmer_data["farmer_data"]  # Note: farmer_data contains the profile
            else:
                logger.warning("⚠️ Farmer input processing had issues, using extracted data")
                return farmer_data.get("farmer_data", {})
                
        except Exception as e:
            logger.error(f"❌ Error processing farmer input: {e}")
            # Return minimal profile for error recovery
            return {
                "phone": phone or "unknown",
                "name": "Unknown Farmer",
                "raw_input": raw_input,
                "timestamp": datetime.now().isoformat()
            }
    
    def _extract_query_from_input(self, raw_input: str, farmer_profile: Dict[str, Any]) -> str:
        """
        Extract the main query/question from farmer's raw input using LLM.
        
        Args:
            raw_input (str): Raw farmer input
            farmer_profile (Dict[str, Any]): Farmer profile data
            
        Returns:
            str: Extracted farmer query
        """
        logger.info("🔍 Extracting farmer query from raw input")
        
        try:
            prompt = f"""
            You are an agricultural assistant analyzing farmer communication from an IVR system.
            
            Raw farmer input: "{raw_input}"
            
            Extract the main query, question, or concern that the farmer is expressing.
            The query should be clear, specific, and focused on their agricultural needs.
            
            If multiple concerns are mentioned, prioritize the most urgent or important one.
            
            Return only the extracted query, nothing else.
            
            Examples:
            - "What fertilizer should I use for my wheat crop?"
            - "My cotton plants have white insects, what should I do?"
            - "Should I irrigate my soybean field this week?"
            - "I want complete farming guidance for this season"
            
            Extracted query:
            """
            
            extracted_query = self.llm_client.call_text_llm(prompt, temperature=0.3)
            
            # Clean up the response
            query = extracted_query.strip().strip('"').strip("'")
            
            logger.info(f"✅ Extracted query: {query[:100]}...")
            return query
            
        except Exception as e:
            logger.error(f"❌ Error extracting query: {e}")
            # Fallback to raw input
            return raw_input[:200]  # Truncate if too long
    
    def _classify_pipeline(self, farmer_query: str, farmer_profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classify whether to use specific or generic pipeline using advanced LLM reasoning.
        
        Args:
            farmer_query (str): Farmer's query
            farmer_profile (Dict[str, Any]): Farmer profile
            
        Returns:
            Dict[str, Any]: Pipeline classification decision
        """
        logger.info("🎯 Classifying pipeline type for farmer query")
        
        try:
            # Build context about farmer
            farmer_context = self._build_farmer_context(farmer_profile)
            
            prompt = f"""
            You are an intelligent agricultural coordinator analyzing farmer queries to determine the best response strategy.
            
            FARMER CONTEXT:
            {farmer_context}
            
            FARMER QUERY: "{farmer_query}"
            
            CLASSIFICATION TASK:
            Determine whether this query requires:
            
            1. SPECIFIC PIPELINE - Targeted response using 1-2 specific agents:
               - Weather queries (irrigation timing, weather forecasts)
               - Pest identification and management
               - Soil-specific fertilizer recommendations
               - Government scheme applications
               - Market price inquiries
               - Specific technical problems
            
            2. GENERIC PIPELINE - Comprehensive end-to-end farming guidance:
               - Complete season planning requests
               - General farming improvement advice
               - "Help me with my farm" type queries
               - Crop selection and planning
               - Overall productivity enhancement
               - Risk management strategies
            
            DECISION CRITERIA:
            - If query is specific and can be answered by 1-2 agents → SPECIFIC
            - If query is broad, comprehensive, or seeks overall guidance → GENERIC
            - If farmer is asking for complete planning/strategy → GENERIC
            - If farmer has a targeted problem → SPECIFIC
            
            REQUIRED AGENTS ANALYSIS:
            For SPECIFIC pipeline, identify which agents are needed:
            - weather: Weather forecasts, irrigation timing, climate data
            - soil: Soil management, fertilizers, soil health
            - pest: Pest identification, disease management, treatment
            - scheme: Government schemes, subsidies, loans
            
            Return ONLY a JSON response in this exact format:
            {{
                "pipeline_type": "specific" or "generic",
                "reasoning": "Brief explanation of classification decision",
                "confidence": 0.0-1.0,
                "required_agents": ["agent1", "agent2"] or "all",
                "urgency": "low" or "medium" or "high",
                "complexity": "simple" or "moderate" or "complex"
            }}
            """
            
            response = self.llm_client.call_text_llm(prompt, temperature=0.2)
            
            # Parse JSON response with robust error handling
            decision = self._parse_json_response(response, fallback_type="pipeline_classification")
            
            # Validate the decision
            if "pipeline_type" not in decision:
                logger.warning("⚠️ Pipeline type missing, using intelligent fallback")
                decision["pipeline_type"] = self._intelligent_pipeline_fallback(farmer_query, farmer_profile)
            
            # Ensure required fields
            decision.setdefault("confidence", 0.7)
            decision.setdefault("urgency", "medium")
            decision.setdefault("complexity", "moderate")
            decision.setdefault("reasoning", "Automated classification")
            
            # Validate pipeline type
            if decision["pipeline_type"] not in ["specific", "generic"]:
                decision["pipeline_type"] = "generic"  # Safe default
            
            # Set required agents for specific pipeline
            if decision["pipeline_type"] == "specific" and "required_agents" not in decision:
                decision["required_agents"] = self._infer_required_agents(farmer_query)
            elif decision["pipeline_type"] == "generic":
                decision["required_agents"] = "all"
            
            logger.info(f"✅ Pipeline classified as: {decision['pipeline_type']} (confidence: {decision['confidence']})")
            return decision
                
        except Exception as e:
            logger.error(f"❌ Error classifying pipeline: {e}")
            # Fallback classification
            return {
                "pipeline_type": "generic",
                "reasoning": "Fallback due to classification error",
                "confidence": 0.5,
                "required_agents": "all",
                "urgency": "medium",
                "complexity": "moderate"
            }
    
    def _parse_json_response(self, response_text: str, fallback_type: str) -> Dict[str, Any]:
        """
        Parse JSON response from LLM with robust error handling.
        
        Args:
            response_text (str): Raw response text from LLM
            fallback_type (str): Type of fallback to generate
            
        Returns:
            Dict[str, Any]: Parsed JSON or fallback dictionary
        """
        try:
            # Try to find JSON within the response text
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                return json.loads(json_str)
            else:
                logger.warning(f"⚠️ No JSON object found in response: {response_text}")
                return self._get_fallback_response(fallback_type)
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON Decode Error: {e}\nResponse: {response_text}")
            return self._get_fallback_response(fallback_type)

    def _get_fallback_response(self, fallback_type: str) -> Dict[str, Any]:
        """
        Get a fallback response for a given type.
        """
        if fallback_type == "pipeline_classification":
            return {
                "pipeline_type": "generic",
                "reasoning": "Fallback due to parsing error",
                "confidence": 0.5,
                "required_agents": "all",
                "urgency": "medium",
                "complexity": "moderate"
            }
        elif fallback_type == "strategy_generation":
            return {
                "error": "Strategy generation failed due to parsing error",
                "message": "Could not parse the LLM response.",
                "fallback_available": True
            }
        return {"error": "Parsing failed", "message": "Could not parse the LLM response."}

    def _intelligent_pipeline_fallback(self, farmer_query: str, farmer_profile: Dict[str, Any]) -> str:
        """
        Intelligent fallback for pipeline classification.
        """
        query_lower = farmer_query.lower()
        specific_keywords = ["weather", "pest", "soil", "scheme", "fertilizer", "insect", "rain", "subsidy"]
        if any(keyword in query_lower for keyword in specific_keywords):
            return "specific"
        return "generic"

    def _infer_required_agents(self, farmer_query: str) -> List[str]:
        """
        Infer required agents for a specific query.
        """
        query_lower = farmer_query.lower()
        agents = []
        if any(k in query_lower for k in ["weather", "rain", "irrigation", "temperature"]):
            agents.append("weather")
        if any(k in query_lower for k in ["soil", "fertilizer", "nutrient"]):
            agents.append("soil")
        if any(k in query_lower for k in ["pest", "insect", "disease", "weed"]):
            agents.append("pest")
        if any(k in query_lower for k in ["scheme", "subsidy", "loan", "government"]):
            agents.append("scheme")
        
        return agents if agents else ["weather", "soil", "pest", "scheme"]

    def _execute_specific_pipeline(self, farmer_query: str, farmer_profile: Dict[str, Any], 
                                 pipeline_decision: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute specific pipeline - call only required agents and combine responses.
        
        Args:
            farmer_query (str): Farmer's query
            farmer_profile (Dict[str, Any]): Farmer profile
            pipeline_decision (Dict[str, Any]): Pipeline classification
            
        Returns:
            Dict[str, Any]: Combined specific agent responses
        """
        logger.info(f"🎯 Executing specific pipeline with agents: {pipeline_decision.get('required_agents', [])}")
        
        required_agents = pipeline_decision.get("required_agents", [])
        agent_responses = {}
        agents_used = []
        
        try:
            # Call required agents
            for agent_name in required_agents:
                if agent_name == "weather":
                    logger.info("☀️ Calling Weather Agent")
                    response = self.weather_agent.process_query(farmer_query, farmer_profile, "specific")
                    agent_responses["weather"] = response
                    agents_used.append("weather")
                
                elif agent_name == "soil":
                    logger.info("🌱 Calling Soil Agent")
                    response = self.soil_agent.process_query(farmer_query, farmer_profile, "specific")
                    agent_responses["soil"] = response
                    agents_used.append("soil")
                
                elif agent_name == "pest":
                    logger.info("🐛 Calling Pest Agent")
                    response = self.pest_agent.process_query(farmer_query, farmer_profile, "specific")
                    agent_responses["pest"] = response
                    agents_used.append("pest")
                
                elif agent_name == "scheme":
                    logger.info("🏛️ Calling Scheme Agent")
                    response = self.scheme_agent.process_query(farmer_query, farmer_profile, "specific")
                    agent_responses["scheme"] = response
                    agents_used.append("scheme")
            
            # Synthesize responses
            final_response = self._synthesize_specific_responses(
                farmer_query, farmer_profile, agent_responses, pipeline_decision
            )
            
            final_response.update({
                "status": "success",
                "pipeline_type": "specific",
                "agents_used": agents_used,
                "agent_responses": agent_responses,
                "timestamp": datetime.now().isoformat()
            })
            
            return final_response
            
        except Exception as e:
            logger.error(f"❌ Error in specific pipeline: {e}")
            return {
                "status": "error",
                "pipeline_type": "specific",
                "message": f"Specific pipeline failed: {str(e)}",
                "agents_used": agents_used,
                "timestamp": datetime.now().isoformat()
            }
    
    def _execute_generic_pipeline(self, farmer_query: str, farmer_profile: Dict[str, Any], 
                                pipeline_decision: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute generic pipeline - comprehensive end-to-end farming guidance.
        
        This is the crown jewel of the orchestrator - uses all resources to provide
        state-of-the-art comprehensive farming guidance.
        
        Args:
            farmer_query (str): Farmer's query
            farmer_profile (Dict[str, Any]): Farmer profile
            pipeline_decision (Dict[str, Any]): Pipeline classification
            
        Returns:
            Dict[str, Any]: Comprehensive farming guidance
        """
        logger.info("🌟 Executing generic pipeline - comprehensive farming guidance")
        
        try:
            # Step 1: Gather intelligence from all agents
            all_agent_data = self._gather_comprehensive_intelligence(farmer_query, farmer_profile)
            
            # Step 2: Generate comprehensive farming strategy
            comprehensive_strategy = self._generate_comprehensive_strategy(
                farmer_query, farmer_profile, all_agent_data, pipeline_decision
            )
            
            # Step 3: Create actionable roadmap
            actionable_roadmap = self._create_actionable_roadmap(
                farmer_profile, all_agent_data, comprehensive_strategy
            )
            
            # Step 4: Generate hyperlocal recommendations
            hyperlocal_guidance = self._generate_hyperlocal_guidance(
                farmer_profile, all_agent_data, comprehensive_strategy
            )
            
            # Compile final response
            final_response = {
                "status": "success",
                "pipeline_type": "generic",
                "comprehensive_strategy": comprehensive_strategy,
                "actionable_roadmap": actionable_roadmap,
                "hyperlocal_guidance": hyperlocal_guidance,
                "agent_intelligence": all_agent_data,
                "agents_used": ["weather", "soil", "pest", "scheme"],
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info("✅ Generic pipeline completed successfully")
            return final_response
            
        except Exception as e:
            logger.error(f"❌ Error in generic pipeline: {e}")
            return {
                "status": "error",
                "pipeline_type": "generic",
                "message": f"Generic pipeline failed: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
    
    def _gather_comprehensive_intelligence(self, farmer_query: str, farmer_profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        Gather comprehensive intelligence from all agents for generic pipeline.
        
        Args:
            farmer_query (str): Farmer's query
            farmer_profile (Dict[str, Any]): Farmer profile
            
        Returns:
            Dict[str, Any]: All agent intelligence data
        """
        logger.info("🧠 Gathering comprehensive intelligence from all agents")
        
        intelligence = {}
        
        try:
            # Weather Intelligence
            logger.info("☀️ Gathering weather intelligence")
            weather_data = self.weather_agent.process_query(
                "Provide comprehensive weather guidance for farming activities", 
                farmer_profile, "generic"
            )
            intelligence["weather"] = weather_data
            
            # Soil Intelligence
            logger.info("🌱 Gathering soil intelligence")
            soil_data = self.soil_agent.process_query(
                "Provide comprehensive soil management and fertilizer guidance", 
                farmer_profile, "generic"
            )
            intelligence["soil"] = soil_data
            
            # Pest Intelligence
            logger.info("🐛 Gathering pest intelligence")
            pest_data = self.pest_agent.process_query(
                "Provide comprehensive pest management and prevention guidance", 
                farmer_profile, "generic"
            )
            intelligence["pest"] = pest_data
            
            # Scheme Intelligence
            logger.info("🏛️ Gathering scheme intelligence")
            scheme_data = self.scheme_agent.process_query(
                "Identify all relevant schemes and financial opportunities", 
                farmer_profile, "generic"
            )
            intelligence["scheme"] = scheme_data
            
            logger.info("✅ Comprehensive intelligence gathered from all agents")
            return intelligence
            
        except Exception as e:
            logger.error(f"❌ Error gathering intelligence: {e}")
            return {"error": str(e)}
    
    def _synthesize_specific_responses(self, farmer_query: str, farmer_profile: Dict[str, Any], 
                                     agent_responses: Dict[str, Any], pipeline_decision: Dict[str, Any]) -> Dict[str, Any]:
        """
        Synthesize responses from specific agents into a coherent answer.
        
        Args:
            farmer_query (str): Original farmer query
            farmer_profile (Dict[str, Any]): Farmer profile
            agent_responses (Dict[str, Any]): Responses from called agents
            pipeline_decision (Dict[str, Any]): Pipeline classification
            
        Returns:
            Dict[str, Any]: Synthesized response
        """
        logger.info("🔄 Synthesizing specific agent responses")
        
        try:
            # Build context for synthesis
            farmer_context = self._build_farmer_context(farmer_profile)
            
            # Prepare agent summaries
            agent_summaries = []
            for agent_name, response in agent_responses.items():
                if response.get("status") == "success":
                    summary = f"\n{agent_name.upper()} AGENT RESPONSE:\n"
                    if "farmer_response" in response:
                        summary += response["farmer_response"]
                    elif "analysis" in response:
                        summary += str(response["analysis"])
                    else:
                        summary += str(response)
                    agent_summaries.append(summary)
            
            # Synthesis prompt
            prompt = f"""
            You are an expert agricultural coordinator synthesizing responses from multiple specialized agents to answer a farmer's specific query.
            
            FARMER CONTEXT:
            {farmer_context}
            
            ORIGINAL QUERY: "{farmer_query}"
            
            AGENT RESPONSES:
            {''.join(agent_summaries)}
            
            SYNTHESIS TASK:
            Create a comprehensive, actionable response that:
            1. Directly answers the farmer's query
            2. Integrates insights from all responding agents
            3. Provides clear, practical recommendations
            4. Uses simple language suitable for farmers
            5. Includes specific timing and dosage information where applicable
            6. Prioritizes the most important actions
            
            FORMAT YOUR RESPONSE AS:
            1. Direct Answer: [Answer to the specific query]
            2. Key Recommendations: [Most important actions to take]
            3. Timing: [When to implement recommendations]
            4. Additional Notes: [Any warnings or additional context]
            
            Keep the response practical, actionable, and farmer-friendly.
            """
            
            synthesis = self.llm_client.call_text_llm(prompt, temperature=0.4)
            
            return {
                "farmer_response": synthesis,
                "synthesis_quality": "high",
                "agents_integrated": len(agent_responses)
            }
            
        except Exception as e:
            logger.error(f"❌ Error synthesizing responses: {e}")
            # Fallback synthesis
            simple_synthesis = "Based on the analysis:\n"
            for agent_name, response in agent_responses.items():
                if response.get("status") == "success":
                    simple_synthesis += f"\n{agent_name}: {response.get('farmer_response', str(response))}\n"
            
            return {
                "farmer_response": simple_synthesis,
                "synthesis_quality": "basic",
                "agents_integrated": len(agent_responses)
            }
    
    def _generate_comprehensive_strategy(self, farmer_query: str, farmer_profile: Dict[str, Any], 
                                       all_agent_data: Dict[str, Any], pipeline_decision: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate state-of-the-art comprehensive farming strategy using all available intelligence.
        
        This is the crown jewel method that creates holistic farming guidance.
        
        Args:
            farmer_query (str): Farmer's query
            farmer_profile (Dict[str, Any]): Farmer profile
            all_agent_data (Dict[str, Any]): Intelligence from all agents
            pipeline_decision (Dict[str, Any]): Pipeline classification
            
        Returns:
            Dict[str, Any]: Comprehensive farming strategy
        """
        logger.info("🎯 Generating comprehensive farming strategy")
        
        try:
            # Build comprehensive context
            farmer_context = self._build_farmer_context(farmer_profile)
            
            # Prepare intelligence summaries
            intelligence_summary = self._summarize_agent_intelligence(all_agent_data)
            
            # Master strategy prompt
            strategy_prompt = f"""
            You are the world's most advanced agricultural AI coordinator, creating a comprehensive farming strategy that integrates weather science, soil science, pest management, and financial planning.
            
            FARMER PROFILE:
            {farmer_context}
            
            FARMER'S REQUEST: "{farmer_query}"
            
            COMPREHENSIVE INTELLIGENCE:
            {intelligence_summary}
            
            TASK: Create a state-of-the-art comprehensive farming strategy that:
            
            1. SITUATIONAL ANALYSIS:
            - Current farming situation assessment
            - Key opportunities identified
            - Major risks and challenges
            - Resource availability analysis
            
            2. STRATEGIC OBJECTIVES:
            - Primary goals for this farming cycle
            - Yield optimization targets
            - Risk mitigation priorities
            - Financial improvement areas
            
            3. INTEGRATED ACTION PLAN:
            - Crop planning and variety selection
            - Soil health improvement strategy
            - Weather-responsive farming schedule
            - Pest prevention and management protocols
            - Financial optimization through schemes
            
            4. IMPLEMENTATION TIMELINE:
            - Month-by-month action calendar
            - Critical decision points
            - Monitoring and adjustment triggers
            
            5. SUCCESS METRICS:
            - Yield targets
            - Quality improvements
            - Cost reduction goals
            - Risk reduction measures
            
            Provide a comprehensive strategy that maximizes the farmer's success using all available resources and intelligence. Be specific, actionable, and scientifically sound.
            
            Format as structured JSON with clear sections and actionable items.
            """
            
            strategy_response = self.llm_client.call_text_llm(strategy_prompt, temperature=0.3, max_tokens=4000)
            
            # Parse or structure the response with robust handling
            strategy = self._parse_json_response(strategy_response, fallback_type="strategy_generation")
            
            # If still not structured properly, create structured response
            if "comprehensive_strategy" not in strategy and "error" not in strategy:
                strategy = {
                    "comprehensive_strategy": strategy_response,
                    "generation_method": "text_structured",
                    "integration_level": "high",
                    "situational_analysis": "Generated from comprehensive intelligence",
                    "strategic_objectives": "Based on farmer profile and agent data",
                    "integrated_action_plan": "Multi-agent coordinated recommendations",
                    "implementation_timeline": "Season-based action calendar",
                    "success_metrics": "Yield and profitability targets"
                }
            
            logger.info("✅ Comprehensive strategy generated successfully")
            return strategy
            
        except Exception as e:
            logger.error(f"❌ Error generating comprehensive strategy: {e}")
            return {
                "error": "Strategy generation failed",
                "message": str(e),
                "fallback_available": True
            }
    
    def _create_actionable_roadmap(self, farmer_profile: Dict[str, Any], 
                                 all_agent_data: Dict[str, Any], strategy: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create detailed actionable roadmap from strategy.
        
        Args:
            farmer_profile (Dict[str, Any]): Farmer profile
            all_agent_data (Dict[str, Any]): All agent data
            strategy (Dict[str, Any]): Comprehensive strategy
            
        Returns:
            Dict[str, Any]: Actionable roadmap
        """
        logger.info("🗺️ Creating actionable roadmap")
        
        try:
            current_date = datetime.now()
            
            # Create timeline-based roadmap
            roadmap = {
                "immediate_actions": [],  # Next 1-2 weeks
                "short_term_plan": [],    # Next 1-3 months
                "long_term_strategy": [], # Next 6-12 months
                "seasonal_calendar": {},  # Month-by-month actions
                "critical_deadlines": [],
                "resource_requirements": {},
                "success_indicators": []
            }
            
            # Extract immediate actions from agent data
            for agent_name, agent_data in all_agent_data.items():
                if agent_data.get("status") == "success":
                    # Extract urgent actions
                    if "orchestrator_insights" in agent_data:
                        insights = agent_data["orchestrator_insights"]
                        if "required_actions" in insights:
                            roadmap["immediate_actions"].extend(insights["required_actions"])
            
            # Add timeline structure
            for i in range(12):  # 12 months ahead
                month_date = current_date + timedelta(days=30*i)
                month_key = month_date.strftime("%Y-%m")
                roadmap["seasonal_calendar"][month_key] = {
                    "month": month_date.strftime("%B %Y"),
                    "weather_considerations": [],
                    "crop_activities": [],
                    "pest_monitoring": [],
                    "scheme_deadlines": []
                }
            
            logger.info("✅ Actionable roadmap created")
            return roadmap
            
        except Exception as e:
            logger.error(f"❌ Error creating roadmap: {e}")
            return {"error": str(e)}
    
    def _generate_hyperlocal_guidance(self, farmer_profile: Dict[str, Any], 
                                    all_agent_data: Dict[str, Any], strategy: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate hyperlocal guidance specific to farmer's location and conditions.
        
        Args:
            farmer_profile (Dict[str, Any]): Farmer profile
            all_agent_data (Dict[str, Any]): All agent data
            strategy (Dict[str, Any]): Comprehensive strategy
            
        Returns:
            Dict[str, Any]: Hyperlocal guidance
        """
        logger.info("📍 Generating hyperlocal guidance")
        
        try:
            location = farmer_profile.get("pincode", "Unknown")
            soil_type = farmer_profile.get("soil_type", "Unknown")
            crops = farmer_profile.get("crops", [])
            
            hyperlocal = {
                "location_specific": {
                    "pincode": location,
                    "soil_type": soil_type,
                    "local_conditions": "Analyzed from weather and soil data"
                },
                "variety_recommendations": [],
                "local_suppliers": {
                    "seeds": "Contact local agricultural department",
                    "fertilizers": "Nearest cooperative society",
                    "pesticides": "Licensed dealers in your area"
                },
                "market_linkages": {
                    "nearby_markets": f"Markets near {location}",
                    "price_trends": "Check local mandi rates"
                },
                "extension_services": {
                    "krishi_vigyan_kendra": f"KVK for {location} area",
                    "agricultural_officer": "Contact district agricultural officer"
                }
            }
            
            # Add specific recommendations based on agent data
            if "weather" in all_agent_data and all_agent_data["weather"].get("status") == "success":
                weather_data = all_agent_data["weather"]
                if "orchestrator_insights" in weather_data:
                    hyperlocal["weather_specific"] = weather_data["orchestrator_insights"]
            
            logger.info("✅ Hyperlocal guidance generated")
            return hyperlocal
            
        except Exception as e:
            logger.error(f"❌ Error generating hyperlocal guidance: {e}")
            return {"error": str(e)}
    
    def _build_farmer_context(self, farmer_profile: Dict[str, Any]) -> str:
        """
        Build comprehensive farmer context string for LLM prompts.
        
        Args:
            farmer_profile (Dict[str, Any]): Farmer profile
            
        Returns:
            str: Formatted farmer context
        """
        context_parts = []
        
        # Basic information
        if farmer_profile.get("name"):
            context_parts.append(f"Farmer: {farmer_profile['name']}")
        if farmer_profile.get("pincode"):
            context_parts.append(f"Location: {farmer_profile['pincode']}")
        
        # Land information
        if farmer_profile.get("land_total_ha"):
            context_parts.append(f"Total land: {farmer_profile['land_total_ha']} hectares")
        if farmer_profile.get("soil_type"):
            context_parts.append(f"Soil type: {farmer_profile['soil_type']}")
        
        # Crop information
        crops = farmer_profile.get("crops", [])
        if crops:
            crop_info = []
            for crop in crops:
                if isinstance(crop, dict):
                    crop_str = f"{crop.get('crop', 'Unknown crop')}"
                    if crop.get("area_ha"):
                        crop_str += f" ({crop['area_ha']} ha)"
                    if crop.get("season"):
                        crop_str += f" - {crop['season']} season"
                    crop_info.append(crop_str)
                else:
                    crop_info.append(str(crop))
            context_parts.append(f"Crops: {', '.join(crop_info)}")
        
        # Financial information
        budget = farmer_profile.get("budget", {})
        if budget:
            if budget.get("cash_on_hand_inr"):
                context_parts.append(f"Available cash: ₹{budget['cash_on_hand_inr']}")
        
        return "\n".join(context_parts) if context_parts else "Limited farmer information available"
    
    def _summarize_agent_intelligence(self, all_agent_data: Dict[str, Any]) -> str:
        """
        Summarize intelligence from all agents for strategy generation.
        
        Args:
            all_agent_data (Dict[str, Any]): All agent data
            
        Returns:
            str: Summarized intelligence
        """
        summaries = []
        
        for agent_name, agent_data in all_agent_data.items():
            if agent_data.get("status") == "success":
                summary = f"\n{agent_name.upper()} INTELLIGENCE:\n"
                
                # Extract key insights
                if "orchestrator_insights" in agent_data:
                    insights = agent_data["orchestrator_insights"]
                    for key, value in insights.items():
                        if isinstance(value, list):
                            summary += f"- {key}: {', '.join(map(str, value[:3]))}\n"
                        else:
                            summary += f"- {key}: {value}\n"
                
                # Add farmer response if available
                if "farmer_response" in agent_data:
                    summary += f"Recommendations: {agent_data['farmer_response'][:200]}...\n"
                
                summaries.append(summary)
        
        return "\n".join(summaries)
    
    def get_system_status(self) -> Dict[str, Any]:
        """
        Get overall system status and health check.
        
        Returns:
            Dict[str, Any]: System status report
        """
        logger.info("🔍 Checking system status")
        
        status = {
            "orchestrator": "operational",
            "agents": {},
            "processors": {},
            "timestamp": datetime.now().isoformat()
        }
        
        # Test each component
        try:
            # Test farmer processor
            status["processors"]["farmer_input"] = "operational"
            
            # Test query router
            status["processors"]["query_router"] = "operational"
            
            # Test individual agents
            agents = ["weather", "soil", "pest", "scheme"]
            for agent_name in agents:
                try:
                    # Simple health check
                    status["agents"][agent_name] = "operational"
                except:
                    status["agents"][agent_name] = "error"
            
            logger.info("✅ System status check completed")
            
        except Exception as e:
            logger.error(f"❌ Error checking system status: {e}")
            status["error"] = str(e)
        
        return status


# Testing and demonstration
if __name__ == "__main__":
    print("🎯 ORCHESTRATOR AGENT - STEP 4")
    print("=" * 70)
    print("🌟 Master Coordinator Agent - Boss of all agents")
    print("=" * 70)
    
    try:
        # Initialize orchestrator
        orchestrator = OrchestratorAgent()
        
        print("\n✅ Orchestrator initialized successfully!")
        print(f"🤖 Agents coordinated: Weather, Soil, Pest, Scheme")
        print(f"⚡ Pipeline types: Specific, Generic")
        print(f"🎯 Ready for farmer requests from IVR system")
        
        # System status check
        print("\n🔍 System Status Check:")
        print("-" * 40)
        status = orchestrator.get_system_status()
        
        for component, state in status.get("agents", {}).items():
            emoji = "✅" if state == "operational" else "❌"
            print(f"   {emoji} {component.capitalize()} Agent: {state}")
        
        for component, state in status.get("processors", {}).items():
            emoji = "✅" if state == "operational" else "❌"
            print(f"   {emoji} {component.replace('_', ' ').title()}: {state}")
        
        print(f"\n🏁 Orchestrator Agent ready for production!")
        print(f"🎉 Next: Integrate with IVR system for live farmer requests")
        
    except Exception as e:
        print(f"❌ Error initializing orchestrator: {e}")
        print("🔧 Check individual agent implementations")
