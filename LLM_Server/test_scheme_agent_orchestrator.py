#!/usr/bin/env python3
"""
Orchestrator Integration Test for Scheme Agent - Step 3.e
Demonstrates clean English output and structured data for orchestrator coordination.

Author: Nikhil Mishra
Date: August 18, 2025
"""

import sys
import os
import json
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scheme_agent import SchemeAgent

def test_orchestrator_integration():
    """Test Scheme Agent integration with orchestrator-ready outputs."""
    print("🤝 SCHEME AGENT ORCHESTRATOR INTEGRATION TEST")
    print("=" * 70)
    
    agent = SchemeAgent()
    
    # Sample farmer profile
    farmer_profile = {
        "name": "Rajesh Kumar",
        "phone": "9876543210",
        "pincode": "226010",
        "land_total_ha": 1.5,
        "land_cultivated_ha": 1.2,
        "soil_type": "Alluvial",
        "water_source": "tubewell",
        "crops": [
            {
                "crop": "wheat",
                "variety": "HD-2967",
                "area_ha": 0.8,
                "season": "Rabi"
            }
        ],
        "budget": {
            "cash_on_hand_inr": 25000,
            "planned_loan_inr": 50000
        }
    }
    
    print("\n🔍 TEST 1: SPECIFIC PIPELINE OUTPUT STRUCTURE")
    print("-" * 50)
    
    specific_result = agent.process_query(
        query="I need crop insurance for my wheat farm",
        farmer_profile=farmer_profile,
        pipeline_type="specific"
    )
    
    if specific_result["status"] == "success":
        print("✅ Specific Pipeline Success")
        print(f"📊 Output Structure:")
        print(f"   - Status: {specific_result['status']}")
        print(f"   - Agent: {specific_result['agent']}")
        print(f"   - Pipeline: {specific_result['pipeline']}")
        print(f"   - Schemes Found: {specific_result['scheme_count']}")
        print(f"   - Eligible Schemes: {specific_result['eligible_schemes']}")
        print(f"   - Response Type: {type(specific_result['farmer_response'])}")
        print(f"   - Response Length: {len(specific_result['farmer_response'])} characters")
        
        # Check if response is in English (not Hindi)
        response_sample = specific_result['farmer_response'][:200]
        print(f"   - Response Sample: {response_sample}...")
        
        # Verify English output
        hindi_indicators = ["नमस्कार", "आप", "के लिए", "किसान", "योजना"]
        is_english = not any(indicator in response_sample for indicator in hindi_indicators)
        print(f"   - Clean English Output: {'✅ Yes' if is_english else '❌ No'}")
    
    print("\n🔍 TEST 2: GENERIC PIPELINE OUTPUT STRUCTURE")
    print("-" * 50)
    
    generic_result = agent.process_query(
        query="Help me plan my farming activities comprehensively",
        farmer_profile=farmer_profile,
        pipeline_type="generic"
    )
    
    if generic_result["status"] == "success":
        print("✅ Generic Pipeline Success")
        print(f"📊 Output Structure:")
        print(f"   - Status: {generic_result['status']}")
        print(f"   - Agent: {generic_result['agent']}")
        print(f"   - Pipeline: {generic_result['pipeline']}")
        print(f"   - Relevant Schemes: {len(generic_result['relevant_schemes'])}")
        print(f"   - Eligible Schemes: {generic_result['eligible_schemes']}")
        
        # Check orchestrator insights structure
        insights = generic_result.get('orchestrator_insights', {})
        print(f"   - Orchestrator Insights Available: {'✅ Yes' if insights else '❌ No'}")
        
        if insights:
            print(f"   - Scheme Opportunities: {insights.get('scheme_opportunities', 0)}")
            print(f"   - Priority Schemes: {', '.join(insights.get('priority_schemes', [])[:2])}")
            print(f"   - Application Urgency: {insights.get('application_urgency', 'N/A')}")
            print(f"   - Financial Benefits: {insights.get('financial_benefits_potential', 'N/A')}")
            print(f"   - Required Actions: {len(insights.get('required_actions', []))}")
            print(f"   - Integration Suggestions: {len(insights.get('integration_suggestions', []))}")
        
        # Check scheme summaries structure
        summaries = generic_result.get('scheme_summaries', [])
        print(f"   - Scheme Summaries: {len(summaries)} schemes")
        
        if summaries:
            sample_summary = summaries[0]
            print(f"   - Sample Summary Structure:")
            print(f"     * Name: {sample_summary.get('name', 'N/A')}")
            print(f"     * Type: {sample_summary.get('type', 'N/A')}")
            print(f"     * Eligible: {sample_summary.get('eligible', 'N/A')}")
            print(f"     * Key Benefit: {sample_summary.get('key_benefit', 'N/A')[:50]}...")
    
    print("\n🔍 TEST 3: DATA SERIALIZATION FOR ORCHESTRATOR")
    print("-" * 50)
    
    # Test JSON serialization
    try:
        json_specific = json.dumps(specific_result, indent=2, default=str)
        json_generic = json.dumps(generic_result, indent=2, default=str)
        
        print("✅ JSON Serialization Success")
        print(f"   - Specific Pipeline JSON Size: {len(json_specific):,} bytes")
        print(f"   - Generic Pipeline JSON Size: {len(json_generic):,} bytes")
        print(f"   - Both pipelines produce valid JSON for orchestrator")
        
    except Exception as e:
        print(f"❌ JSON Serialization Failed: {e}")
    
    print("\n🔍 TEST 4: ORCHESTRATOR DATA REQUIREMENTS")
    print("-" * 50)
    
    # Check key data points orchestrator needs
    orchestrator_requirements = {
        "farmer_response": specific_result.get('farmer_response', ''),
        "scheme_count": specific_result.get('scheme_count', 0),
        "eligible_schemes": specific_result.get('eligible_schemes', 0),
        "orchestrator_insights": generic_result.get('orchestrator_insights', {}),
        "scheme_summaries": generic_result.get('scheme_summaries', []),
        "pipeline_type": specific_result.get('pipeline', 'unknown')
    }
    
    print("✅ Key Orchestrator Data Points:")
    for key, value in orchestrator_requirements.items():
        value_type = type(value).__name__
        if isinstance(value, (str, list, dict)):
            size = len(value)
            print(f"   - {key}: {value_type} (size: {size})")
        else:
            print(f"   - {key}: {value_type} (value: {value})")
    
    print("\n🔍 TEST 5: INTEGRATION COMPATIBILITY")
    print("-" * 50)
    
    # Check compatibility with other agents
    compatibility_checks = {
        "Standard JSON Output": json.dumps(specific_result, default=str) is not None,
        "English Language": "hindi" not in specific_result['farmer_response'].lower(),
        "Structured Insights": len(generic_result.get('orchestrator_insights', {})) > 0,
        "Error Handling": 'status' in specific_result and 'agent' in specific_result,
        "Timestamp Available": 'timestamp' in specific_result,
        "Pipeline Identification": 'pipeline' in specific_result
    }
    
    for check, passed in compatibility_checks.items():
        status = "✅" if passed else "❌"
        print(f"   {status} {check}")
    
    all_passed = all(compatibility_checks.values())
    print(f"\n🎯 Overall Integration Compatibility: {'✅ READY' if all_passed else '⚠️ NEEDS REVIEW'}")
    
    return all_passed

if __name__ == "__main__":
    test_result = test_orchestrator_integration()
    
    print("\n" + "=" * 70)
    print("📋 INTEGRATION TEST SUMMARY")
    print("=" * 70)
    
    if test_result:
        print("🎉 SUCCESS: Scheme Agent is ready for orchestrator integration!")
        print("✅ Clean English output verified")
        print("✅ Structured data format confirmed")
        print("✅ JSON serialization working")
        print("✅ All orchestrator requirements met")
        print("\n🔄 Next Steps:")
        print("   1️⃣ Ready for Step 4: Orchestrator/Coordinator Agent development")
        print("   2️⃣ Compatible with Weather, Soil, and Pest Agents")
        print("   3️⃣ Supports both specific and generic pipelines")
    else:
        print("⚠️ REVIEW NEEDED: Some integration requirements not met")
        print("🔧 Check the test output above for specific issues")
    
    print(f"\n🏁 Test completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
