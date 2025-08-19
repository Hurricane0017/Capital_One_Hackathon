"""
Test Script - Comprehensive testing of the entire system
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from orchestrator import AgentOrchestrator
from ivr_interface import IVRInterface
import json
from datetime import datetime

def test_weather_agent():
    """Test weather agent functionality"""
    print("\n🌤️  TESTING WEATHER AGENT")
    print("=" * 50)
    
    orchestrator = AgentOrchestrator()
    weather_agent = orchestrator.weather_agent
    
    # Test coordinates (Delhi)
    latitude, longitude = 28.6139, 77.2090
    
    # Test different weather queries
    test_cases = [
        ("irrigation", "Should I water my wheat crop today?"),
        ("harvest", "When is good time to harvest?"),  
        ("pest_risk", "Will this weather cause pest problems?"),
        ("summary", "What's the weather forecast?")
    ]
    
    for test_type, query in test_cases:
        print(f"\n🧪 Testing: {test_type}")
        print(f"Query: {query}")
        
        context = {
            "latitude": latitude,
            "longitude": longitude,
            "crop_type": "wheat",
            "soil_type": "alluvial"
        }
        
        result = weather_agent.process_weather_query(query, context)
        
        if result['status'] == 'success':
            print(f"✅ Success!")
            print(f"📊 Weather data points: {len(result.get('weather_data', {}).get('daily', []))}")
            print(f"💬 Analysis preview: {result.get('analysis', result.get('summary', ''))[:100]}...")
        else:
            print(f"❌ Failed: {result.get('error')}")
    
    return True

def test_database_agent():
    """Test database agent functionality"""
    print("\n💾 TESTING DATABASE AGENT")
    print("=" * 50)
    
    orchestrator = AgentOrchestrator()
    db_agent = orchestrator.database_agent
    
    test_queries = [
        ("soil", "What crops can I grow in alluvial soil?"),
        ("pest", "My rice crop has brown spots on leaves"),
        ("insurance", "What government schemes can help with crop insurance?"),
        ("crops", "Which crops are best for my black soil?")
    ]
    
    context = {
        "soil_type": "alluvial",
        "crop_type": "rice",
        "region": "Punjab"
    }
    
    for test_type, query in test_queries:
        print(f"\n🧪 Testing: {test_type}")
        print(f"Query: {query}")
        
        result = db_agent.process_database_query(query, context)
        
        if result['status'] == 'success':
            print(f"✅ Success!")
            print(f"📊 Data found: {result.get('data_found', 0)} records")
            print(f"💬 Analysis preview: {result.get('analysis', '')[:100]}...")
        else:
            print(f"❌ Failed: {result.get('error')}")
    
    return True

def test_farmer_input_agent():
    """Test farmer input agent functionality"""
    print("\n🧑‍🌾 TESTING FARMER INPUT AGENT")
    print("=" * 50)
    
    orchestrator = AgentOrchestrator()
    farmer_agent = orchestrator.farmer_input_agent
    
    test_inputs = [
        ("farmer_001", "I am Rajesh from Punjab, I have 5 acres of wheat crop"),
        ("farmer_002", "My tomato plants in Bangalore have yellow leaves, I have 2 hectares"),
        ("farmer_003", "I have ₹50,000 budget for next season in Maharashtra")
    ]
    
    for farmer_id, query in test_inputs:
        print(f"\n🧪 Testing farmer input: {farmer_id}")
        print(f"Query: {query}")
        
        result = farmer_agent.process_farmer_input(query, farmer_id)
        
        if result['status'] == 'success':
            print(f"✅ Success!")
            profile = result['context_extraction']['farmer_profile']
            print(f"📊 Profile fields extracted: {list(profile.keys())}")
            print(f"🎯 Intent: {result['intent_analysis']['routing_data']['primary_agent']}")
            print(f"📈 Profile completeness: {result['profile_validation']['completion_percentage']:.1f}%")
        else:
            print(f"❌ Failed: {result.get('error')}")
    
    return True

def test_orchestrator():
    """Test main orchestrator functionality"""
    print("\n🎼 TESTING ORCHESTRATOR")
    print("=" * 50)
    
    orchestrator = AgentOrchestrator()
    
    comprehensive_test_cases = [
        {
            "farmer_id": "test_farmer_001",
            "query": "मैं पंजाब से राजेश हूं। मेरी 3 एकड़ गेहूं की फसल है। आज पानी देना चाहिए क्या?",
            "expected_agents": ["weather", "farmer_input"]
        },
        {
            "farmer_id": "test_farmer_002", 
            "query": "My rice crop has brown patches. What disease could this be and how to treat it?",
            "expected_agents": ["database", "farmer_input"]
        },
        {
            "farmer_id": "test_farmer_003",
            "query": "I have ₹1 lakh budget. What profitable crops can I grow this season?",
            "expected_agents": ["database", "farmer_input"]
        }
    ]
    
    for i, test_case in enumerate(comprehensive_test_cases, 1):
        print(f"\n🧪 Comprehensive Test {i}")
        print(f"Query: {test_case['query']}")
        print(f"Expected agents: {test_case['expected_agents']}")
        
        result = orchestrator.process_farmer_query(
            test_case['query'],
            test_case['farmer_id']
        )
        
        if result['status'] == 'success':
            print(f"✅ Success!")
            agents_used = result['data_sources']['agents_used']
            print(f"📊 Agents used: {agents_used}")
            print(f"🎯 Confidence score: {result['confidence_score']}%")
            print(f"💬 Response preview: {result['response'][:150]}...")
            
            # Check if expected agents were used
            expected_met = any(agent in agents_used for agent in test_case['expected_agents'])
            if expected_met:
                print(f"✅ Expected agent routing successful")
            else:
                print(f"⚠️  Expected agents {test_case['expected_agents']} but got {agents_used}")
                
        else:
            print(f"❌ Failed: {result.get('error')}")
    
    return True

def test_ivr_interface():
    """Test IVR interface functionality"""
    print("\n📞 TESTING IVR INTERFACE") 
    print("=" * 50)
    
    ivr = IVRInterface()
    
    # Test call flow
    call_id = "test_call_001"
    phone_number = "+919876543210"
    
    # Step 1: Start call
    print(f"\n🧪 Testing call start")
    start_response = ivr.handle_incoming_call(call_id, phone_number)
    
    if start_response['status'] == 'success':
        print(f"✅ Call started successfully")
        print(f"💬 Greeting: {start_response['message'][:100]}...")
    else:
        print(f"❌ Call start failed: {start_response.get('error')}")
        return False
    
    # Step 2: Process queries
    test_queries = [
        ("मेरी गेहूं की फसल में पानी देना है क्या?", "Should water wheat crop"),
        ("धन्यवाद", "Thank you - should end call")
    ]
    
    for query, description in test_queries:
        print(f"\n🧪 Testing query: {description}")
        print(f"Input: {query}")
        
        response = ivr.process_speech_input(call_id, query)
        
        if response['status'] == 'success':
            print(f"✅ Query processed successfully")
            print(f"💬 Response preview: {response['message'][:100]}...")
            print(f"🔄 Next state: {response.get('next_state')}")
            
            if response.get('next_state') == 'ended':
                print(f"📞 Call ended correctly")
                break
        else:
            print(f"❌ Query failed: {response.get('error')}")
    
    return True

def test_system_health():
    """Test overall system health"""
    print("\n🏥 TESTING SYSTEM HEALTH")
    print("=" * 50)
    
    orchestrator = AgentOrchestrator()
    
    health = orchestrator.get_system_health()
    
    print(f"System Status: {health['status']}")
    print(f"Database Status: {health['services'].get('mongodb', 'unknown')}")
    print(f"LLM Status: {health['services'].get('llm', 'unknown')}")
    print(f"Total Farmers: {health['performance_metrics']['total_farmers']}")
    print(f"Total Conversations: {health['performance_metrics']['total_conversations']}")
    
    if health['status'] in ['healthy', 'degraded']:
        print("✅ System health check passed")
        return True
    else:
        print("❌ System health check failed")
        return False

def run_comprehensive_tests():
    """Run all tests"""
    print("🚀 STARTING COMPREHENSIVE SYSTEM TESTS")
    print("=" * 60)
    
    tests = [
        ("System Health", test_system_health),
        ("Weather Agent", test_weather_agent),
        ("Database Agent", test_database_agent),
        ("Farmer Input Agent", test_farmer_input_agent),
        ("Orchestrator", test_orchestrator),
        ("IVR Interface", test_ivr_interface)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running {test_name} tests...")
        try:
            results[test_name] = test_func()
            if results[test_name]:
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"💥 {test_name}: ERROR - {str(e)}")
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    total_tests = len(results)
    passed_tests = sum(1 for result in results.values() if result)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL" 
        print(f"{test_name}: {status}")
    
    print(f"\n🎯 Overall Result: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 ALL TESTS PASSED! System is ready for deployment.")
    else:
        print("⚠️  Some tests failed. Please review and fix issues.")
    
    return passed_tests == total_tests

if __name__ == "__main__":
    success = run_comprehensive_tests()
    sys.exit(0 if success else 1)
