#!/usr/bin/env python3
"""
Simple IVR Input Example
Shows the exact way to input farmer text and get orchestrated response

Author: Nikhil Mishra
Date: August 18, 2025
"""

from orchestrator_agent import OrchestratorAgent

# Example 1: Simple usage
def simple_example():
    print("🎯 SIMPLE IVR INPUT EXAMPLE")
    print("=" * 50)
    
    # Initialize orchestrator (this coordinates all 4 agents)
    orchestrator = OrchestratorAgent()
    
    # Farmer's raw text input from IVR voice-to-text
    farmer_text = """
    Hello, my name is Ravi Kumar. I am from Lucknow, UP 226010. 
    I have 2 hectares wheat crop. My plants are looking yellow and there are 
    small green bugs on the leaves. Also, should I water the crop today? 
    The weather seems cloudy.
    """
    
    farmer_phone = "9876543210"
    
    print(f"📱 Farmer Phone: {farmer_phone}")
    print(f"🗣️ Farmer Text: {farmer_text.strip()}")
    print("\n⚡ Processing through orchestrator...")
    
    # THIS IS THE KEY LINE - MAIN ENTRY POINT
    result = orchestrator.process_farmer_request(farmer_text, farmer_phone)
    
    # Display result
    print("\n📊 RESULT:")
    print("-" * 30)
    
    if result.get("status") == "success":
        print(f"✅ Success!")
        print(f"🎯 Pipeline: {result['orchestrator_metadata']['pipeline_used']}")
        print(f"🤖 Agents Used: {', '.join(result.get('agents_used', []))}")
        
        if "farmer_response" in result:
            print(f"\n💬 Response to Farmer:")
            print(f"{result['farmer_response'][:300]}...")
        
        print(f"\n📈 Confidence: {result['orchestrator_metadata']['confidence_score']}")
    else:
        print(f"❌ Error: {result.get('message', 'Unknown error')}")
    
    return result

if __name__ == "__main__":
    simple_example()
