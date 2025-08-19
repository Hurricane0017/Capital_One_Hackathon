#!/usr/bin/env python3
"""
End-to-End Test Script for Orchestrator Agent

This script allows for testing the orchestrator agent with plain English text input,
simulating a request from the IVR system. It demonstrates the full pipeline from
farmer input to the final orchestrated response.

Author: Nikhil Mishra
Date: August 18, 2025
"""

import os
import sys
import json
import logging

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from orchestrator_agent import OrchestratorAgent
from logging_config import setup_logging

# Setup logging for the test script
logger = setup_logging('OrchestratorTest')

def run_test(plain_text_input: str, farmer_phone: str):
    """
    Runs a single end-to-end test for the orchestrator agent.

    Args:
        plain_text_input (str): The plain English text from the "farmer".
        farmer_phone (str): The phone number of the farmer.
    """
    logger.info(f"--- Starting Test for Farmer: {farmer_phone} ---")
    logger.info(f"Input Text: '{plain_text_input}'")

    try:
        # Initialize the orchestrator agent
        orchestrator = OrchestratorAgent()
        logger.info("Orchestrator agent initialized.")

        # Process the request
        response = orchestrator.process_farmer_request(
            raw_farmer_input=plain_text_input,
            farmer_phone=farmer_phone
        )

        logger.info("Orchestrator processing complete.")

        # Print the final response
        print("\n--- Orchestrator Final Response ---")
        print(response)
        print("------------------------------------")

        if isinstance(response, str) and len(response) > 0:
            logger.info("Test PASSED: Orchestrator returned a valid string response.")
        else:
            logger.warning("Test COMPLETED with issues: Orchestrator returned an invalid response.")

    except Exception as e:
        logger.error(f"Test FAILED with an exception: {e}", exc_info=True)
        print(f"\n--- Test FAILED ---")
        print(f"An unexpected error occurred: {e}")
        print("---------------------")

if __name__ == "__main__":
    # --- Configuration for the test ---
    # You can change these values to test different scenarios.

    # Scenario 1: Specific query about pests
    farmer_1_phone = "9876001234"
    farmer_1_input = "I am Pankaj Thakur, phone 9876001234, PIN 175001. You have my permission. Total land 0.8 hectare; cultivating 0.6 hectare in Rabi. Soil is loam. Rainfed. Planning garden peas, variety AP-3, sowing on 15 October 2025; harvest by end of January. I have 40,000 rupees cash, may borrow 20k. Not in insurance. Nearest market Mandi town. I prefer weekly guidance in the evening. I am interested in going organic."

    # # Scenario 2: Generic query for overall guidance
    # farmer_2_phone = "8877665544"
    # farmer_2_input = "I am a small farmer from Lucknow, Uttar Pradesh with 1.5 hectares of alluvial soil. I grow wheat. I need complete guidance for this season to improve my yield and income."

    # # Scenario 3: Specific query about weather and irrigation
    # farmer_3_phone = "7766554433"
    # farmer_3_input = "I am Kishorilal. I have a farm near Mumbai with black soil. I am growing cotton. Should I irrigate my crop in the next 5 days?"

    # --- Run the tests ---
    print("Starting Orchestrator Agent End-to-End Tests...")

    # Run Test 1
    print("\nRunning Test 1: Specific Pest Query")
    run_test(farmer_1_input, farmer_1_phone)

    # # Run Test 2
    # print("\nRunning Test 2: Generic Guidance Query")
    # run_test(farmer_2_input, farmer_2_phone)

    # # Run Test 3
    # print("\nRunning Test 3: Specific Weather Query")
    # run_test(farmer_3_input, farmer_3_phone)

    print("\nAll tests completed. Check the logs in the 'logs' folder for detailed information.")
