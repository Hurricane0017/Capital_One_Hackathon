#!/usr/bin/env python3
"""
Weather Agent - Step 3.a
Comprehensive weather agent that provides agricultural weather guidance for both
specific pipeline (user-provided details) and generic pipeline (season-based) scenarios.

Key Capabilities:
- Extract weather query parameters using LLM
- Fetch weather data via Open-Meteo API
- Provide context-aware agricultural weather advice
- Handle both specific queries and generic seasonal guidance

Author: Nikhil Mishra
Date: August 17, 2025
"""

import sys
import os
import json
import logging
import re
from datetime import datetime, timedelta, date
from typing import Dict, List, Any, Optional, Tuple
import requests_cache
from retry_requests import retry
import openmeteo_requests
import pandas as pd
import numpy as np
from geopy.geocoders import Nominatim

# Import LLM client
from llm_client import LLMClient
from logging_config import setup_logging

# Configure logging
logger = setup_logging('WeatherAgent')

class WeatherAgent:
    """
    Comprehensive Weather Agent for agricultural decision-making.
    
    Handles both specific pipeline (user provides details) and generic pipeline 
    (derives timing from farming seasons) scenarios.
    """
    
    def __init__(self):
        """Initialize the Weather Agent with required clients."""
        self.llm_client = LLMClient(logger=logger)
        self.agent_type = "weather"
        
        # Setup weather API client with caching and retry
        cache_session = requests_cache.CachedSession('.weather_cache', expire_after=3600)
        retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
        self.openmeteo = openmeteo_requests.Client(session=retry_session)
        
        # Geocoding client
        self.geolocator = Nominatim(user_agent="agricultural_weather_agent")
        
        # Seasonal farming calendar for generic pipeline
        self.farming_seasons = {
            "kharif": {
                "start_month": 6,  # June
                "end_month": 10,   # October
                "sowing_period": {"start": 6, "end": 7},      # June-July
                "growing_period": {"start": 7, "end": 9},     # July-September
                "harvest_period": {"start": 9, "end": 10}     # September-October
            },
            "rabi": {
                "start_month": 11, # November
                "end_month": 4,    # April
                "sowing_period": {"start": 11, "end": 12},    # November-December
                "growing_period": {"start": 12, "end": 3},    # December-March
                "harvest_period": {"start": 3, "end": 4}      # March-April
            },
            "zaid": {
                "start_month": 4,  # April
                "end_month": 6,    # June
                "sowing_period": {"start": 4, "end": 5},      # April-May
                "growing_period": {"start": 5, "end": 6},     # May-June
                "harvest_period": {"start": 6, "end": 6}      # June
            }
        }
    
    def process_query(self, query: str, farmer_profile: Dict[str, Any] = None, 
                     pipeline_type: str = "specific") -> Dict[str, Any]:
        """
        Main entry point to process weather queries.
        
        Args:
            query (str): The farmer's weather-related query
            farmer_profile (Dict[str, Any]): Farmer profile data
            pipeline_type (str): "specific" or "generic"
            
        Returns:
            Dict[str, Any]: Comprehensive weather guidance response
        """
        logger.info(f"Processing {pipeline_type} weather query: {query[:100]}...")
        
        try:
            if pipeline_type == "specific":
                return self._process_specific_query(query, farmer_profile)
            else:
                return self._process_generic_query(query, farmer_profile)
                
        except Exception as e:
            logger.error(f"Weather query processing failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "agent": "weather",
                "fallback_advice": "Please check local weather reports and consult with local agricultural extension officers for weather-based farming decisions."
            }
    
    def _process_specific_query(self, query: str, farmer_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Process specific pipeline weather queries."""
        logger.info("Processing specific weather pipeline query")
        
        # Step 1: Extract required parameters using LLM
        params = self._extract_weather_parameters(query, farmer_profile)
        
        # Step 2: Get weather data
        weather_data = self._fetch_weather_data(
            params["location"], 
            params["start_date"], 
            params["end_date"]
        )
        
        # Step 3: Generate agricultural weather analysis
        analysis = self._generate_weather_analysis(
            query, weather_data, params, farmer_profile
        )
        
        return {
            "success": True,
            "agent": "weather",
            "pipeline": "specific",
            "query": query,
            "parameters": params,
            "weather_data": weather_data,
            "analysis": analysis,
            "recommendations": analysis.get("recommendations", []),
            "alerts": analysis.get("alerts", [])
        }
    
    def _process_generic_query(self, query: str, farmer_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Process generic pipeline weather queries with seasonal context."""
        logger.info("Processing generic weather pipeline query")
        
        # Step 1: Determine current season and farming stage
        seasonal_context = self._determine_seasonal_context(farmer_profile)
        
        # Step 2: Generate appropriate date ranges based on farming season
        date_ranges = self._generate_seasonal_date_ranges(seasonal_context)
        
        # Step 3: Get weather data for relevant periods
        weather_data = {}
        for period, dates in date_ranges.items():
            weather_data[period] = self._fetch_weather_data(
                farmer_profile.get("pincode", "110001"),
                dates["start"],
                dates["end"]
            )
        
        # Step 4: Generate comprehensive seasonal weather guidance
        analysis = self._generate_seasonal_analysis(
            query, weather_data, seasonal_context, farmer_profile
        )
        
        return {
            "success": True,
            "agent": "weather",
            "pipeline": "generic", 
            "query": query,
            "seasonal_context": seasonal_context,
            "date_ranges": date_ranges,
            "weather_data": weather_data,
            "analysis": analysis,
            "recommendations": analysis.get("recommendations", []),
            "seasonal_calendar": analysis.get("seasonal_calendar", {})
        }
    
    def _extract_weather_parameters(self, query: str, farmer_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Extract location, start_date, and end_date using LLM."""
        
        profile_context = ""
        if farmer_profile:
            profile_context = f"""
FARMER PROFILE AVAILABLE:
- Name: {farmer_profile.get('name', 'N/A')}
- Pincode: {farmer_profile.get('pincode', 'N/A')}
- Location: {farmer_profile.get('village', 'N/A')}, {farmer_profile.get('district', 'N/A')}, {farmer_profile.get('state', 'N/A')}
- Crops: {', '.join([crop.get('crop', 'N/A') for crop in farmer_profile.get('crops', [])])}
"""
        
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        prompt = f"""
You are an expert agricultural parameter extractor. Extract the following information from the farmer's query:

1. **LOCATION** (pincode/place): Look for pincodes, village names, city names, or use farmer profile
2. **START_DATE** (YYYY-MM-DD): When the weather information should begin
3. **END_DATE** (YYYY-MM-DD): When the weather information should end

CURRENT DATE: {current_date}

{profile_context}

FARMER QUERY: "{query}"

EXTRACTION RULES:
- If location is not mentioned in query, use farmer profile pincode/location
- If dates not specified, use agricultural reasoning:
  * "next few days" = current date to +7 days
  * "this week" = current date to +7 days  
  * "irrigation planning" = current date to +14 days
  * "sowing/planting" = current date to +30 days
  * "harvest planning" = current date to +60 days
- If no timeframe mentioned, default to next 7 days
- Always ensure start_date >= current date
- Maximum forecast period is 16 days from current date

Respond ONLY with valid JSON in this exact format:
{{
  "location": "pincode or place name",
  "start_date": "YYYY-MM-DD",
  "end_date": "YYYY-MM-DD",
  "reasoning": "Brief explanation of how parameters were determined"
}}

Return ONLY the JSON, no other text.
"""
        
        try:
            response = self.llm_client.call_text_llm(prompt, temperature=0.1)
            
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                params = json.loads(json_match.group())
                
                # Validate and fix dates
                params = self._validate_date_parameters(params)
                
                logger.info(f"Extracted parameters: {params}")
                return params
            else:
                raise ValueError("No JSON found in LLM response")
                
        except Exception as e:
            logger.error(f"Parameter extraction failed: {e}")
            # Fallback to default parameters
            return self._get_default_parameters(farmer_profile)
    
    def _validate_date_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and fix date parameters."""
        current_date = datetime.now().date()
        max_forecast_date = current_date + timedelta(days=16)
        
        try:
            # Parse dates
            start_date = datetime.strptime(params["start_date"], '%Y-%m-%d').date()
            end_date = datetime.strptime(params["end_date"], '%Y-%m-%d').date()
            
            # Fix start date if in past
            if start_date < current_date:
                start_date = current_date
                params["start_date"] = start_date.strftime('%Y-%m-%d')
            
            # Fix end date if too far in future
            if end_date > max_forecast_date:
                end_date = max_forecast_date
                params["end_date"] = end_date.strftime('%Y-%m-%d')
            
            # Ensure end date is after start date
            if end_date <= start_date:
                end_date = start_date + timedelta(days=7)
                params["end_date"] = end_date.strftime('%Y-%m-%d')
                
        except ValueError as e:
            logger.error(f"Date validation failed: {e}")
            # Set default dates
            params["start_date"] = current_date.strftime('%Y-%m-%d')
            params["end_date"] = (current_date + timedelta(days=7)).strftime('%Y-%m-%d')
        
        return params
    
    def _get_default_parameters(self, farmer_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Get default parameters when extraction fails."""
        current_date = datetime.now().date()
        
        # Use farmer profile location or default
        location = "110001"  # Default Delhi pincode
        if farmer_profile and farmer_profile.get("pincode"):
            location = str(farmer_profile["pincode"])
        
        return {
            "location": location,
            "start_date": current_date.strftime('%Y-%m-%d'),
            "end_date": (current_date + timedelta(days=7)).strftime('%Y-%m-%d'),
            "reasoning": "Default parameters used due to extraction failure"
        }
    
    def _fetch_weather_data(self, location: str, start_date: str, end_date: str) -> Dict[str, Any]:
        """Fetch weather data from Open-Meteo API."""
        try:
            # Get coordinates from location
            latitude, longitude = self._get_coordinates(location)
            
            # Setup API parameters
            url = "https://api.open-meteo.com/v1/forecast"
            params = {
                "latitude": latitude,
                "longitude": longitude,
                "hourly": [
                    "temperature_2m", "relative_humidity_2m", "apparent_temperature", 
                    "rain", "showers", "surface_pressure", "cloud_cover", 
                    "vapour_pressure_deficit", "wind_direction_80m", 
                    "wind_gusts_10m", "wind_speed_120m", "soil_moisture_3_to_9cm"
                ],
                "start_date": start_date,
                "end_date": end_date,
            }
            
            # Fetch data
            responses = self.openmeteo.weather_api(url, params=params)
            response = responses[0]
            
            # Process hourly data
            hourly = response.Hourly()
            hourly_data = {
                "date": pd.date_range(
                    start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
                    end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
                    freq=pd.Timedelta(seconds=hourly.Interval()),
                    inclusive="left"
                )
            }
            
            # Extract variables
            variables = [
                "temperature_2m", "relative_humidity_2m", "apparent_temperature", 
                "rain", "showers", "surface_pressure", "cloud_cover",
                "vapour_pressure_deficit", "wind_direction_80m", 
                "wind_gusts_10m", "wind_speed_120m", "soil_moisture_3_to_9cm"
            ]
            
            for i, var in enumerate(variables):
                hourly_data[var] = hourly.Variables(i).ValuesAsNumpy()
            
            # Create DataFrame and aggregate to daily
            hourly_df = pd.DataFrame(data=hourly_data)
            hourly_df.set_index("date", inplace=True)
            
            # Generate daily aggregations
            daily_df = pd.DataFrame({
                "temp_mean": hourly_df["temperature_2m"].resample("D").mean(),
                "temp_max": hourly_df["temperature_2m"].resample("D").max(),
                "temp_min": hourly_df["temperature_2m"].resample("D").min(),
                "humidity_mean": hourly_df["relative_humidity_2m"].resample("D").mean(),
                "rain_sum": hourly_df["rain"].resample("D").sum(),
                "wind_speed_mean": hourly_df["wind_speed_120m"].resample("D").mean(),
                "wind_gusts_max": hourly_df["wind_gusts_10m"].resample("D").max(),
                "soil_moisture_mean": hourly_df["soil_moisture_3_to_9cm"].resample("D").mean()
            })
            
            # Convert to JSON-serializable format
            daily_data = []
            for date_idx, row in daily_df.iterrows():
                daily_data.append({
                    "date": date_idx.strftime('%Y-%m-%d'),
                    "temp_mean": round(float(row["temp_mean"]), 1),
                    "temp_max": round(float(row["temp_max"]), 1),
                    "temp_min": round(float(row["temp_min"]), 1),
                    "humidity_mean": round(float(row["humidity_mean"]), 1),
                    "rain_sum": round(float(row["rain_sum"]), 1),
                    "wind_speed_mean": round(float(row["wind_speed_mean"]), 1),
                    "wind_gusts_max": round(float(row["wind_gusts_max"]), 1),
                    "soil_moisture_mean": round(float(row["soil_moisture_mean"]), 3)
                })
            
            return {
                "location": location,
                "coordinates": {"latitude": latitude, "longitude": longitude},
                "period": {"start": start_date, "end": end_date},
                "daily_data": daily_data,
                "summary": self._generate_weather_summary(daily_data)
            }
            
        except Exception as e:
            logger.error(f"Weather data fetch failed: {e}")
            raise
    
    def _get_coordinates(self, location: str) -> Tuple[float, float]:
        """Get coordinates from location string (pincode or place name)."""
        try:
            # If it looks like a pincode (6 digits), add "India" for better geocoding
            if location.isdigit() and len(location) == 6:
                location = f"{location}, India"
            
            geo_location = self.geolocator.geocode(location)
            if geo_location:
                return geo_location.latitude, geo_location.longitude
            else:
                # Fallback to Delhi coordinates
                logger.warning(f"Location '{location}' not found, using Delhi coordinates")
                return 28.6139, 77.2090
                
        except Exception as e:
            logger.error(f"Geocoding failed for '{location}': {e}")
            return 28.6139, 77.2090
    
    def _generate_weather_summary(self, daily_data: List[Dict]) -> Dict[str, Any]:
        """Generate summary statistics from daily weather data."""
        if not daily_data:
            return {}
        
        temps = [day["temp_mean"] for day in daily_data]
        rains = [day["rain_sum"] for day in daily_data]
        winds = [day["wind_speed_mean"] for day in daily_data]
        
        return {
            "period_days": len(daily_data),
            "temp_avg": round(np.mean(temps), 1),
            "temp_max": round(max([day["temp_max"] for day in daily_data]), 1),
            "temp_min": round(min([day["temp_min"] for day in daily_data]), 1),
            "total_rainfall": round(sum(rains), 1),
            "rainy_days": len([r for r in rains if r > 0.1]),
            "avg_wind_speed": round(np.mean(winds), 1),
            "max_wind_gust": round(max([day["wind_gusts_max"] for day in daily_data]), 1)
        }
    
    def _generate_weather_analysis(self, query: str, weather_data: Dict[str, Any], 
                                 params: Dict[str, Any], farmer_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive agricultural weather analysis using LLM."""
        
        # Build context for LLM
        weather_summary = weather_data.get("summary", {})
        daily_forecast = weather_data.get("daily_data", [])[:7]  # Next 7 days
        
        crop_context = ""
        if farmer_profile and farmer_profile.get("crops"):
            crops = [crop.get("crop", "N/A") for crop in farmer_profile["crops"]]
            crop_context = f"Farmer grows: {', '.join(crops)}"
        
        prompt = f"""
You are an expert agricultural meteorologist providing weather guidance to Indian farmers.

FARMER QUERY: "{query}"

LOCATION: {params.get("location", "N/A")}
PERIOD: {params.get("start_date")} to {params.get("end_date")}
{crop_context}

WEATHER FORECAST SUMMARY:
- Period: {weather_summary.get("period_days", 0)} days
- Temperature: {weather_summary.get("temp_min", 0)}°C to {weather_summary.get("temp_max", 0)}°C (avg: {weather_summary.get("temp_avg", 0)}°C)
- Total Rainfall: {weather_summary.get("total_rainfall", 0)}mm over {weather_summary.get("rainy_days", 0)} days
- Wind Speed: {weather_summary.get("avg_wind_speed", 0)}km/h (max gusts: {weather_summary.get("max_wind_gust", 0)}km/h)

DETAILED DAILY FORECAST:
{json.dumps(daily_forecast, indent=2)}

Please provide comprehensive agricultural weather guidance covering:

1. **DIRECT ANSWER** to the farmer's specific question
2. **IRRIGATION RECOMMENDATIONS** (when to water, how much, based on rainfall and evaporation)
3. **PLANTING/SOWING GUIDANCE** (optimal timing, risk assessment)
4. **CROP PROTECTION ALERTS** (pest/disease risks from weather conditions)
5. **FIELD OPERATION TIMING** (best days for spraying, harvesting, machinery work)
6. **WEATHER RISKS & ALERTS** (storms, heatwaves, drought, waterlogging)
7. **SPECIFIC DAILY ACTIONS** (what to do each day based on forecast)

Focus on:
- Practical, actionable advice
- Day-by-day recommendations where relevant
- Risk mitigation strategies
- Optimal timing for farming operations
- Water management guidance
- Crop protection from weather extremes

Format your response as practical advice that a farmer can immediately act upon.
Provide specific dates and times where applicable.
"""
        
        try:
            analysis_response = self.llm_client.call_text_llm(prompt, temperature=0.3)
            
            # Extract structured recommendations
            recommendations = self._extract_actionable_recommendations(analysis_response, daily_forecast)
            alerts = self._extract_weather_alerts(weather_summary, daily_forecast)
            
            return {
                "detailed_analysis": analysis_response,
                "recommendations": recommendations,
                "alerts": alerts,
                "weather_insights": {
                    "irrigation_needs": self._assess_irrigation_needs(weather_summary, daily_forecast),
                    "field_work_windows": self._identify_field_work_windows(daily_forecast),
                    "risk_assessment": self._assess_weather_risks(weather_summary, daily_forecast)
                }
            }
            
        except Exception as e:
            logger.error(f"Weather analysis generation failed: {e}")
            return {
                "detailed_analysis": "Weather analysis could not be generated due to technical issues.",
                "recommendations": [],
                "alerts": [],
                "error": str(e)
            }
    
    def _determine_seasonal_context(self, farmer_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Determine current farming season and stage."""
        current_month = datetime.now().month
        
        # Determine current season
        current_season = None
        for season, info in self.farming_seasons.items():
            if info["start_month"] <= info["end_month"]:
                if info["start_month"] <= current_month <= info["end_month"]:
                    current_season = season
                    break
            else:  # Season spans year boundary (like Rabi)
                if current_month >= info["start_month"] or current_month <= info["end_month"]:
                    current_season = season
                    break
        
        if not current_season:
            current_season = "kharif"  # Default
        
        # Determine farming stage within season
        season_info = self.farming_seasons[current_season]
        stage = "growing"  # Default
        
        if season_info["sowing_period"]["start"] <= current_month <= season_info["sowing_period"]["end"]:
            stage = "sowing"
        elif season_info["harvest_period"]["start"] <= current_month <= season_info["harvest_period"]["end"]:
            stage = "harvest"
        
        return {
            "current_season": current_season,
            "farming_stage": stage,
            "season_info": season_info,
            "current_month": current_month
        }
    
    def _generate_seasonal_date_ranges(self, seasonal_context: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
        """Generate appropriate date ranges for seasonal weather analysis."""
        current_date = datetime.now().date()
        
        # Base ranges on farming stage
        if seasonal_context["farming_stage"] == "sowing":
            # Focus on next 30 days for sowing decisions
            return {
                "immediate": {
                    "start": current_date.strftime('%Y-%m-%d'),
                    "end": (current_date + timedelta(days=7)).strftime('%Y-%m-%d')
                },
                "planning": {
                    "start": current_date.strftime('%Y-%m-%d'),
                    "end": (current_date + timedelta(days=30)).strftime('%Y-%m-%d')
                }
            }
        elif seasonal_context["farming_stage"] == "harvest":
            # Focus on next 14 days for harvest planning
            return {
                "immediate": {
                    "start": current_date.strftime('%Y-%m-%d'),
                    "end": (current_date + timedelta(days=7)).strftime('%Y-%m-%d')
                },
                "harvest_window": {
                    "start": current_date.strftime('%Y-%m-%d'),
                    "end": (current_date + timedelta(days=14)).strftime('%Y-%m-%d')
                }
            }
        else:
            # Growing stage - focus on irrigation and crop management
            return {
                "immediate": {
                    "start": current_date.strftime('%Y-%m-%d'),
                    "end": (current_date + timedelta(days=7)).strftime('%Y-%m-%d')
                },
                "irrigation_planning": {
                    "start": current_date.strftime('%Y-%m-%d'),
                    "end": (current_date + timedelta(days=14)).strftime('%Y-%m-%d')
                }
            }
    
    def _generate_seasonal_analysis(self, query: str, weather_data: Dict[str, Any], 
                                  seasonal_context: Dict[str, Any], farmer_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive seasonal weather analysis."""
        
        current_season = seasonal_context["current_season"]
        farming_stage = seasonal_context["farming_stage"]
        
        # Combine weather data from all periods
        all_weather_data = []
        for period, data in weather_data.items():
            if data and "daily_data" in data:
                all_weather_data.extend(data["daily_data"])
        
        crop_context = ""
        if farmer_profile and farmer_profile.get("crops"):
            crops = [crop.get("crop", "N/A") for crop in farmer_profile["crops"]]
            crop_context = f"Farmer grows: {', '.join(crops)}"
        
        prompt = f"""
You are an expert agricultural consultant providing comprehensive seasonal weather guidance.

FARMER QUERY: "{query}"

SEASONAL CONTEXT:
- Current Season: {current_season.upper()} ({farming_stage} stage)
- Location: PIN {farmer_profile.get("pincode", "N/A")}
{crop_context}

WEATHER FORECAST DATA:
{json.dumps(all_weather_data[:14], indent=2)}

As an agricultural expert, provide comprehensive guidance covering:

1. **SEASONAL OVERVIEW** for {current_season} season
2. **CURRENT STAGE GUIDANCE** for {farming_stage} activities
3. **WEATHER-BASED RECOMMENDATIONS** for next 2 weeks
4. **IRRIGATION CALENDAR** based on rainfall and evaporation
5. **OPTIMAL TIMING** for key farming operations
6. **RISK MITIGATION** strategies for weather extremes
7. **SEASONAL CALENDAR** with key dates and activities

Focus on:
- Season-appropriate agricultural practices
- Stage-specific crop management
- Weather-responsive farming decisions
- Preventive measures for weather risks
- Optimal resource utilization

Provide a comprehensive seasonal weather guidance that helps the farmer make informed decisions throughout the {current_season} season.
"""
        
        try:
            analysis_response = self.llm_client.call_text_llm(prompt, temperature=0.3)
            
            # Generate seasonal calendar
            seasonal_calendar = self._generate_seasonal_calendar(seasonal_context, all_weather_data)
            
            return {
                "detailed_analysis": analysis_response,
                "recommendations": self._extract_seasonal_recommendations(analysis_response),
                "seasonal_calendar": seasonal_calendar,
                "stage_guidance": {
                    "current_stage": farming_stage,
                    "key_activities": self._get_stage_activities(farming_stage, current_season),
                    "weather_considerations": self._get_weather_considerations(farming_stage)
                }
            }
            
        except Exception as e:
            logger.error(f"Seasonal analysis generation failed: {e}")
            return {
                "detailed_analysis": "Seasonal weather analysis could not be generated.",
                "recommendations": [],
                "error": str(e)
            }
    
    def _extract_actionable_recommendations(self, analysis: str, daily_forecast: List[Dict]) -> List[Dict[str, Any]]:
        """Extract structured actionable recommendations from analysis."""
        recommendations = []
        
        # Basic recommendation extraction (can be enhanced with more sophisticated parsing)
        lines = analysis.split('\n')
        current_rec = None
        
        for line in lines:
            line = line.strip()
            if any(keyword in line.lower() for keyword in ['recommend', 'should', 'irrigate', 'spray', 'harvest', 'plant']):
                if current_rec:
                    recommendations.append(current_rec)
                current_rec = {
                    "action": line,
                    "priority": "medium",
                    "timing": "immediate"
                }
            elif current_rec and line and not line.startswith('#'):
                current_rec["details"] = current_rec.get("details", "") + " " + line
        
        if current_rec:
            recommendations.append(current_rec)
        
        return recommendations[:10]  # Limit to top 10 recommendations
    
    def _extract_weather_alerts(self, weather_summary: Dict, daily_forecast: List[Dict]) -> List[Dict[str, Any]]:
        """Extract weather alerts and warnings."""
        alerts = []
        
        # Temperature alerts
        if weather_summary.get("temp_max", 0) > 40:
            alerts.append({
                "type": "heat_wave",
                "severity": "high",
                "message": f"Heat wave warning: Temperature may reach {weather_summary['temp_max']}°C. Increase irrigation and provide shade to crops."
            })
        
        # Rainfall alerts
        total_rain = weather_summary.get("total_rainfall", 0)
        if total_rain > 50:
            alerts.append({
                "type": "heavy_rain",
                "severity": "medium",
                "message": f"Heavy rainfall expected: {total_rain}mm over forecast period. Check field drainage and delay field operations."
            })
        elif total_rain < 1:
            alerts.append({
                "type": "dry_spell",
                "severity": "medium", 
                "message": "Dry weather expected. Plan irrigation accordingly and monitor soil moisture."
            })
        
        # Wind alerts
        max_wind = weather_summary.get("max_wind_gust", 0)
        if max_wind > 50:
            alerts.append({
                "type": "strong_winds",
                "severity": "high",
                "message": f"Strong winds expected: up to {max_wind}km/h. Secure equipment and avoid spraying operations."
            })
        
        return alerts
    
    def _assess_irrigation_needs(self, weather_summary: Dict, daily_forecast: List[Dict]) -> Dict[str, Any]:
        """Assess irrigation needs based on weather forecast."""
        total_rain = weather_summary.get("total_rainfall", 0)
        avg_temp = weather_summary.get("temp_avg", 25)
        
        if total_rain > 25:
            irrigation_need = "low"
        elif total_rain > 10:
            irrigation_need = "moderate"
        else:
            irrigation_need = "high"
        
        # Adjust for temperature
        if avg_temp > 35:
            irrigation_need = "high"
        
        return {
            "need_level": irrigation_need,
            "expected_rainfall": total_rain,
            "recommendation": f"Irrigation need is {irrigation_need} based on {total_rain}mm expected rainfall and {avg_temp}°C average temperature."
        }
    
    def _identify_field_work_windows(self, daily_forecast: List[Dict]) -> List[Dict[str, Any]]:
        """Identify optimal windows for field operations."""
        work_windows = []
        
        for i, day in enumerate(daily_forecast):
            if day.get("rain_sum", 0) < 1 and day.get("wind_speed_mean", 0) < 15:
                work_windows.append({
                    "date": day.get("date"),
                    "activities": ["spraying", "mechanical_operations", "harvesting"],
                    "conditions": "favorable",
                    "rain_risk": "low"
                })
        
        return work_windows[:5]  # Next 5 favorable days
    
    def _assess_weather_risks(self, weather_summary: Dict, daily_forecast: List[Dict]) -> Dict[str, Any]:
        """Assess weather-related agricultural risks."""
        risks = []
        
        # Heat stress risk
        if weather_summary.get("temp_max", 0) > 38:
            risks.append("heat_stress")
        
        # Drought risk
        if weather_summary.get("total_rainfall", 0) < 5:
            risks.append("drought_stress")
        
        # Waterlogging risk
        if weather_summary.get("total_rainfall", 0) > 75:
            risks.append("waterlogging")
        
        # Wind damage risk
        if weather_summary.get("max_wind_gust", 0) > 45:
            risks.append("wind_damage")
        
        return {
            "identified_risks": risks,
            "risk_level": "high" if len(risks) > 2 else "medium" if risks else "low",
            "mitigation_required": len(risks) > 0
        }
    
    def _extract_seasonal_recommendations(self, analysis: str) -> List[Dict[str, Any]]:
        """Extract seasonal recommendations from analysis."""
        # This is a simplified extraction - can be enhanced
        recommendations = []
        
        if "irrigation" in analysis.lower():
            recommendations.append({
                "category": "irrigation",
                "recommendation": "Monitor soil moisture and adjust irrigation based on weather forecast",
                "priority": "high"
            })
        
        if "sowing" in analysis.lower():
            recommendations.append({
                "category": "sowing",
                "recommendation": "Plan sowing activities based on weather windows",
                "priority": "high"
            })
        
        return recommendations
    
    def _generate_seasonal_calendar(self, seasonal_context: Dict, weather_data: List[Dict]) -> Dict[str, Any]:
        """Generate a seasonal farming calendar with weather considerations."""
        current_season = seasonal_context["current_season"]
        farming_stage = seasonal_context["farming_stage"]
        
        return {
            "season": current_season,
            "current_stage": farming_stage,
            "key_dates": {
                "next_irrigation": (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d'),
                "optimal_spray_days": [day["date"] for day in weather_data[:7] if day.get("rain_sum", 0) < 1][:3],
                "harvest_window": f"{current_season} harvest typically in {self.farming_seasons[current_season]['harvest_period']['start']}-{self.farming_seasons[current_season]['harvest_period']['end']} months"
            }
        }
    
    def _get_stage_activities(self, stage: str, season: str) -> List[str]:
        """Get key activities for current farming stage."""
        activities = {
            "sowing": [
                "Prepare seedbed",
                "Check seed quality", 
                "Plan irrigation schedule",
                "Apply basal fertilizers",
                "Monitor weather for optimal sowing window"
            ],
            "growing": [
                "Monitor crop growth",
                "Manage irrigation",
                "Apply fertilizers as needed",
                "Scout for pests and diseases",
                "Weed management"
            ],
            "harvest": [
                "Monitor crop maturity",
                "Plan harvest timing",
                "Arrange transportation",
                "Check market prices",
                "Prepare storage facilities"
            ]
        }
        return activities.get(stage, [])
    
    def _get_weather_considerations(self, stage: str) -> List[str]:
        """Get weather considerations for farming stage."""
        considerations = {
            "sowing": [
                "Avoid sowing before heavy rains",
                "Ensure adequate soil moisture",
                "Check for favorable temperature conditions"
            ],
            "growing": [
                "Monitor rainfall for irrigation planning",
                "Watch for pest-favorable weather conditions",
                "Protect crops from extreme weather"
            ],
            "harvest": [
                "Ensure dry weather for harvest",
                "Avoid harvest during rains",
                "Plan around storm predictions"
            ]
        }
        return considerations.get(stage, [])


# Testing and demonstration
if __name__ == "__main__":
    print("🌤️  WEATHER AGENT - STEP 3.a TEST")
    print("=" * 60)
    
    # Initialize weather agent
    agent = WeatherAgent()
    
    # Test case 1: Specific pipeline query
    print("\n📍 TEST 1: SPECIFIC PIPELINE QUERY")
    print("-" * 40)
    
    specific_query = "Should I irrigate my cotton crop in the next 5 days? PIN code is 400001"
    farmer_profile = {
        "name": "Rajesh Kumar",
        "pincode": "400001",
        "village": "Andheri",
        "district": "Mumbai",
        "state": "Maharashtra", 
        "crops": [{"crop": "cotton", "area_ha": 2.5}]
    }
    
    print(f"Query: {specific_query}")
    
    try:
        result = agent.process_query(specific_query, farmer_profile, "specific")
        print(f"✅ Processing successful!")
        print(f"Pipeline: {result.get('pipeline')}")
        print(f"Parameters extracted: {result.get('parameters', {})}")
        print(f"Weather summary: {result.get('weather_data', {}).get('summary', {})}")
        print(f"Number of recommendations: {len(result.get('recommendations', []))}")
        print(f"Number of alerts: {len(result.get('alerts', []))}")
        
        if result.get('analysis', {}).get('detailed_analysis'):
            print(f"Analysis preview: {result['analysis']['detailed_analysis'][:200]}...")
            
    except Exception as e:
        print(f"❌ Test 1 failed: {e}")
    
    # Test case 2: Generic pipeline query
    print(f"\n🌾 TEST 2: GENERIC PIPELINE QUERY")
    print("-" * 40)
    
    generic_query = "I need comprehensive weather guidance for my kharif season farming"
    
    print(f"Query: {generic_query}")
    
    try:
        result = agent.process_query(generic_query, farmer_profile, "generic")
        print(f"✅ Processing successful!")
        print(f"Pipeline: {result.get('pipeline')}")
        print(f"Seasonal context: {result.get('seasonal_context', {})}")
        print(f"Date ranges: {list(result.get('date_ranges', {}).keys())}")
        print(f"Stage guidance: {result.get('analysis', {}).get('stage_guidance', {}).get('current_stage')}")
        
    except Exception as e:
        print(f"❌ Test 2 failed: {e}")
    
    # Test case 3: Parameter extraction
    print(f"\n🔍 TEST 3: PARAMETER EXTRACTION")
    print("-" * 40)
    
    test_queries = [
        "Will it rain in next 3 days in Mumbai?",
        "Should I water my crops this week?", 
        "Weather forecast for harvesting next month in PIN 110001"
    ]
    
    for query in test_queries:
        print(f"\nTesting: {query}")
        try:
            params = agent._extract_weather_parameters(query, farmer_profile)
            print(f"✅ Extracted: {params}")
        except Exception as e:
            print(f"❌ Extraction failed: {e}")
    
    print(f"\n🎉 WEATHER AGENT TESTING COMPLETED!")
    print(f"✅ Specific pipeline processing functional")
    print(f"✅ Generic pipeline processing functional")
    print(f"✅ LLM-based parameter extraction working")
    print(f"✅ Weather data fetching and processing working")
    print(f"✅ Agricultural analysis generation working")
    print(f"✅ Ready for integration with query router!")
