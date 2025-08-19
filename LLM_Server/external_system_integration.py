#!/usr/bin/env python3
"""
External System Integration Example
Shows how to connect the Orchestrator Agent to an external system that provides plain English farmer input.

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

# Setup logging
logger = setup_logging('ExternalSystemIntegration')

class ExternalSystemConnector:
    """
    Connector class to integrate with external systems that provide farmer input.
    """
    
    def __init__(self):
        """Initialize the connector with the orchestrator agent."""
        self.orchestrator = OrchestratorAgent()
        logger.info("✅ External System Connector initialized with Orchestrator Agent")
    
    def process_farmer_text(self, farmer_text: str, farmer_phone: str = None) -> str:
        """
        Main function to call from external systems.
        
        Args:
            farmer_text (str): Plain English text from farmer
            farmer_phone (str, optional): Farmer's phone number
            
        Returns:
            str: Plain English response for the farmer
        """
        logger.info(f"🌾 Processing farmer text from external system")
        logger.info(f"Input: {farmer_text[:100]}...")
        
        try:
            # Call the orchestrator's main function
            response = self.orchestrator.process_farmer_request(
                raw_farmer_input=farmer_text,
                farmer_phone=farmer_phone
            )
            
            logger.info("✅ Successfully processed farmer request")
            logger.info(f"Response length: {len(response)} characters")
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Error processing farmer text: {e}")
            return f"Sorry, we encountered an error while processing your request. Please try again later."
    
    def batch_process_farmers(self, farmer_requests: list) -> list:
        """
        Process multiple farmer requests in batch.
        
        Args:
            farmer_requests (list): List of dictionaries with 'text' and optional 'phone' keys
            
        Returns:
            list: List of responses
        """
        logger.info(f"📦 Processing batch of {len(farmer_requests)} farmer requests")
        
        responses = []
        for i, request in enumerate(farmer_requests):
            logger.info(f"Processing request {i+1}/{len(farmer_requests)}")
            
            farmer_text = request.get('text', '')
            farmer_phone = request.get('phone', None)
            
            response = self.process_farmer_text(farmer_text, farmer_phone)
            responses.append({
                'request_id': i,
                'farmer_phone': farmer_phone,
                'response': response
            })
        
        logger.info(f"✅ Completed batch processing of {len(farmer_requests)} requests")
        return responses


# Example usage and testing
if __name__ == "__main__":
    print("🔗 EXTERNAL SYSTEM INTEGRATION EXAMPLE")
    print("=" * 60)
    
    # Initialize the connector
    connector = ExternalSystemConnector()
    
    # Example 1: Single farmer request
    print("\n📞 Example 1: Single Farmer Request")
    print("-" * 40)
    
    farmer_input = """
    Hello, I am Rajesh Kumar from village near Pune, Maharashtra. 
    My phone number is 9876543210. I have 2 acres of black soil land. 
    I am growing cotton this season. There are some white insects on my plants. 
    What should I do? Also, are there any government schemes I can apply for?
    """
    
    response = connector.process_farmer_text(farmer_input, "9876543210")
    print(f"🌾 Farmer Input: {farmer_input.strip()}")
    print(f"\n🤖 System Response:\n{response}")
    
    # Example 2: Batch processing
    print("\n\n📦 Example 2: Batch Processing")
    print("-" * 40)
    
    batch_requests = [
        {
            "text": "I am Sunita from UP. I grow wheat. Need complete farming guidance.",
            "phone": "8765432109"
        },
        {
            "text": "My name is Mahesh. I have problem with soil. It's not giving good yield.",
            "phone": "7654321098"
        },
        {
            "text": "Weather is changing too much. Should I irrigate my maize crop now?",
            "phone": "6543210987"
        }
    ]
    
    batch_responses = connector.batch_process_farmers(batch_requests)
    
    for i, response_data in enumerate(batch_responses):
        print(f"\n--- Batch Request {i+1} ---")
        print(f"Phone: {response_data['farmer_phone']}")
        print(f"Response: {response_data['response'][:200]}...")
        print("-" * 30)
    
    print(f"\n✅ Integration examples completed successfully!")
    print(f"🎯 Use connector.process_farmer_text() in your external system")


# API-style integration functions for different external systems

def api_endpoint_handler(request_data: dict) -> dict:
    """
    Example API endpoint handler that external systems can call.
    
    Args:
        request_data (dict): Should contain 'farmer_text' and optionally 'farmer_phone'
        
    Returns:
        dict: Response with status and farmer_response
    """
    try:
        connector = ExternalSystemConnector()
        
        farmer_text = request_data.get('farmer_text', '')
        farmer_phone = request_data.get('farmer_phone', None)
        
        if not farmer_text:
            return {
                "status": "error",
                "message": "farmer_text is required",
                "farmer_response": None
            }
        
        response = connector.process_farmer_text(farmer_text, farmer_phone)
        
        return {
            "status": "success",
            "message": "Request processed successfully",
            "farmer_response": response
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Processing failed: {str(e)}",
            "farmer_response": None
        }


def webhook_handler(farmer_text: str, farmer_phone: str = None) -> str:
    """
    Simple webhook handler for external systems.
    
    Args:
        farmer_text (str): Plain English farmer input
        farmer_phone (str): Optional farmer phone number
        
    Returns:
        str: Plain English response
    """
    connector = ExternalSystemConnector()
    return connector.process_farmer_text(farmer_text, farmer_phone)


def csv_batch_processor(csv_file_path: str) -> str:
    """
    Process farmer requests from a CSV file.
    
    Args:
        csv_file_path (str): Path to CSV file with columns 'farmer_text' and 'farmer_phone'
        
    Returns:
        str: Path to output CSV file with responses
    """
    import pandas as pd
    
    try:
        # Read input CSV
        df = pd.read_csv(csv_file_path)
        
        # Initialize connector
        connector = ExternalSystemConnector()
        
        # Process each row
        responses = []
        for index, row in df.iterrows():
            farmer_text = row.get('farmer_text', '')
            farmer_phone = row.get('farmer_phone', None)
            
            response = connector.process_farmer_text(farmer_text, farmer_phone)
            responses.append(response)
        
        # Add responses to dataframe
        df['system_response'] = responses
        
        # Save output CSV
        output_path = csv_file_path.replace('.csv', '_with_responses.csv')
        df.to_csv(output_path, index=False)
        
        return output_path
        
    except Exception as e:
        logger.error(f"❌ Error processing CSV: {e}")
        return None
