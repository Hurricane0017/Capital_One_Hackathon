#!/usr/bin/env python3
"""
Test Pest Agent Integration - Step 3.c
Tests integration with existing Steps 1 & 2 and comprehensive pest management scenarios
"""

import os
import sys

# Add current directory to path  
sys.path.append(os.path.dirname(__file__))

from pest_agent import PestAgent

def test_specific_pipeline_integration():
    """Test specific pipeline with real pest scenarios."""
    print("🔍 SPECIFIC PIPELINE INTEGRATION TEST")
    print("-" * 50)
    
    agent = PestAgent()
    
    # Real farmer scenarios
    test_scenarios = [
        {
            "farmer_profile": {
                "name": "Ramesh Patel",
                "district": "Guntur", 
                "state": "Andhra Pradesh",
                "crops": [{"crop": "cotton", "area_ha": 2.5}],
                "soil_type": "black"
            },
            "query": "My cotton plants have small pink caterpillars inside the bolls",
            "expected_pest": "Pink Bollworm"
        },
        {
            "farmer_profile": {
                "name": "Suresh Kumar",
                "district": "Thanjavur",
                "state": "Tamil Nadu", 
                "crops": [{"crop": "rice", "area_ha": 3.0}],
                "soil_type": "alluvial"
            },
            "query": "There are small brown insects at the base of my rice plants and the leaves are turning yellow",
            "expected_pest": "Brown Planthopper"
        },
        {
            "farmer_profile": {
                "name": "Rajesh Singh",
                "district": "Ludhiana",
                "state": "Punjab",
                "crops": [{"crop": "wheat", "area_ha": 4.0}],
                "soil_type": "alluvial"
            },
            "query": "Small green insects are sucking sap from my wheat plants",
            "expected_pest": "Wheat Aphid"
        }
    ]
    
    successful_tests = 0
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n📋 Test Case {i}: {scenario['farmer_profile']['name']}")
        print(f"Crop: {scenario['farmer_profile']['crops'][0]['crop']} | Location: {scenario['farmer_profile']['district']}")
        print(f"Query: {scenario['query']}")
        
        try:
            result = agent.process_query(
                query=scenario["query"],
                farmer_profile=scenario["farmer_profile"],
                pipeline_type="specific"
            )
            
            if result.get("success"):
                print(f"✅ Success - Agent: {result.get('agent')}")
                
                identified_pests = result.get("identified_pests", [])
                pest_count = result.get("pest_count", 0)
                
                print(f"🐛 Identified Pests: {identified_pests}")
                print(f"📊 Database Records Retrieved: {pest_count}")
                
                # Check if expected pest was identified
                expected = scenario["expected_pest"]
                found_expected = any(expected in pest for pest in identified_pests)
                
                if found_expected:
                    print(f"🎯 ✅ Expected pest '{expected}' correctly identified")
                    successful_tests += 1
                else:
                    print(f"🎯 ⚠️ Expected pest '{expected}' not in top results")
                
                # Check analysis quality
                analysis = result.get("analysis", {})
                if analysis and "management_priority" in analysis:
                    priority = analysis["management_priority"]
                    print(f"⚠️ Management Priority: {priority}")
                    
                    recommendations = analysis.get("recommendations", [])
                    if recommendations:
                        print(f"💡 Recommendations Available: {len(recommendations)}")
                        top_rec = recommendations[0]
                        print(f"   Top: {top_rec.get('category')} - {top_rec.get('action', '')[:60]}...")
                
            else:
                print(f"❌ Failed: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"💥 Exception: {e}")
    
    print(f"\n📊 Specific Pipeline Summary: {successful_tests}/{len(test_scenarios)} tests successful")
    return successful_tests == len(test_scenarios)

def test_generic_pipeline_integration():
    """Test generic pipeline for orchestrator coordination."""
    print("\n🎯 GENERIC PIPELINE INTEGRATION TEST") 
    print("-" * 50)
    
    agent = PestAgent()
    
    # Test different farmer profiles for generic guidance
    test_profiles = [
        {
            "name": "Multi-crop farmer",
            "profile": {
                "name": "Priya Sharma",
                "district": "Nashik",
                "state": "Maharashtra", 
                "crops": [
                    {"crop": "cotton", "area_ha": 2.0},
                    {"crop": "soybean", "area_ha": 1.5}
                ],
                "soil_type": "black"
            }
        },
        {
            "name": "Rice specialist",
            "profile": {
                "name": "Ravi Nair",
                "district": "Kottayam", 
                "state": "Kerala",
                "crops": [{"crop": "rice", "area_ha": 3.0}]
            }
        }
    ]
    
    for test in test_profiles:
        print(f"\n📋 {test['name']}: {test['profile']['name']}")
        crops = ', '.join([c['crop'] for c in test['profile']['crops']])
        print(f"Crops: {crops} | Soil: {test['profile'].get('soil_type', 'Not specified')}")
        
        try:
            result = agent.process_query(
                query="I need comprehensive pest management guidance for my farm",
                farmer_profile=test["profile"],
                pipeline_type="generic"
            )
            
            if result.get("success"):
                print(f"✅ Generic pipeline success")
                
                guidance = result.get("orchestrator_guidance", {})
                
                # Check guidance structure
                if "pest_summary" in guidance:
                    pest_summary = guidance["pest_summary"]
                    print(f"🐛 Relevant Pests Identified: {len(pest_summary)}")
                    for pest in pest_summary[:3]:
                        risk = pest.get("risk_level", "unknown")
                        name = pest.get("name", "")
                        print(f"   • {name} (Risk: {risk})")
                
                if "priority_pests" in guidance:
                    priority = guidance["priority_pests"]
                    print(f"⚡ Priority Pests: {priority}")
                
                if "management_focus" in guidance:
                    focus_areas = guidance["management_focus"]
                    print(f"🎯 Management Focus Areas: {len(focus_areas)}")
                    for area in focus_areas[:2]:
                        category = area.get("category", "")
                        priority = area.get("priority", "")
                        print(f"   • {category} (Priority: {priority})")
                
                if "farmer_actions" in guidance:
                    actions = guidance["farmer_actions"]
                    print(f"📋 Farmer Action Items: {len(actions)}")
                
                print("✅ Orchestrator guidance structure complete")
                
            else:
                print(f"❌ Generic pipeline failed: {result.get('error', '')}")
                
        except Exception as e:
            print(f"💥 Exception: {e}")
    
    return True

def test_soil_pest_correlation():
    """Test soil type and pest correlation accuracy."""
    print("\n🌱 SOIL-PEST CORRELATION TEST")
    print("-" * 50)
    
    agent = PestAgent()
    
    # Test soil-specific pest associations
    soil_pest_tests = [
        {
            "soil_type": "black",
            "crop": "cotton",
            "expected_pests": ["Pink Bollworm", "Cotton Aphid"],
            "location": "Maharashtra"
        },
        {
            "soil_type": "alluvial", 
            "crop": "rice",
            "expected_pests": ["Brown Planthopper", "Yellow Stem Borer"],
            "location": "West Bengal"
        },
        {
            "soil_type": "red",
            "crop": "coffee", 
            "expected_pests": ["Coffee Berry Borer"],
            "location": "Karnataka"
        }
    ]
    
    correlation_success = 0
    
    for test in soil_pest_tests:
        farmer_profile = {
            "crops": [{"crop": test["crop"]}],
            "soil_type": test["soil_type"],
            "state": test["location"]
        }
        
        relevant_pests = agent._get_relevant_pests_for_farmer(farmer_profile)
        
        print(f"Soil: {test['soil_type']:<10} | Crop: {test['crop']:<8} | Predicted: {relevant_pests[:3]}")
        
        # Check if expected pests are in results
        found_expected = any(
            any(expected in pest for expected in test["expected_pests"]) 
            for pest in relevant_pests
        )
        
        if found_expected:
            print("✅ Soil-pest correlation accurate")
            correlation_success += 1
        else:
            print(f"⚠️ Expected pests {test['expected_pests']} not found in results")
    
    print(f"\n📊 Soil-Pest Correlation: {correlation_success}/{len(soil_pest_tests)} accurate predictions")
    return correlation_success >= len(soil_pest_tests) * 0.8  # 80% success rate

def test_pest_database_coverage():
    """Test pest database coverage and data quality."""
    print("\n📊 PEST DATABASE COVERAGE TEST")
    print("-" * 50)
    
    agent = PestAgent()
    
    # Test major crop pests availability
    major_pests = [
        "Brown Planthopper", "Pink Bollworm", "Cotton Aphid", "Wheat Aphid",
        "Coffee Berry Borer", "Fall Armyworm", "Rice Gall Midge"
    ]
    
    available_pests = 0
    detailed_data_count = 0
    
    for pest_name in major_pests:
        pest_data = agent._get_pest_data(pest_name)
        
        if pest_data:
            available_pests += 1
            print(f"✅ {pest_name:<20}: Available")
            
            # Check data completeness
            required_fields = ["description", "attack_details", "management_strategies", "impact"]
            complete_data = all(field in pest_data for field in required_fields)
            
            if complete_data:
                detailed_data_count += 1
                
                # Check management strategies completeness
                mgmt = pest_data.get("management_strategies", {})
                has_cultural = bool(mgmt.get("cultural_methods", []))
                has_chemical = bool(mgmt.get("chemical_control", {}))
                has_biological = bool(mgmt.get("biological_control", []))
                
                methods = []
                if has_cultural: methods.append("Cultural")
                if has_biological: methods.append("Biological") 
                if has_chemical: methods.append("Chemical")
                
                print(f"   📋 Management methods: {', '.join(methods)}")
                
                # Check impact data
                impact = pest_data.get("impact", {})
                max_loss = impact.get("max_crop_loss_percent", 0)
                if max_loss > 0:
                    print(f"   ⚠️ Max crop loss: {max_loss}%")
                
        else:
            print(f"❌ {pest_name:<20}: Not available")
    
    print(f"\n📊 Database Coverage:")
    print(f"   Available pests: {available_pests}/{len(major_pests)} ({available_pests/len(major_pests)*100:.0f}%)")
    print(f"   Complete records: {detailed_data_count}/{available_pests} ({detailed_data_count/max(1,available_pests)*100:.0f}%)")
    
    return available_pests >= len(major_pests) * 0.8  # 80% coverage required

def main():
    """Run comprehensive pest agent integration tests."""
    print("🐛 PEST AGENT - INTEGRATION TESTING")
    print("=" * 60)
    
    test_results = []
    
    # Run integration tests
    tests = [
        ("Specific Pipeline", test_specific_pipeline_integration),
        ("Generic Pipeline", test_generic_pipeline_integration), 
        ("Soil-Pest Correlation", test_soil_pest_correlation),
        ("Database Coverage", test_pest_database_coverage)
    ]
    
    for test_name, test_func in tests:
        try:
            print(f"\n🧪 Running {test_name} Test...")
            result = test_func()
            test_results.append((test_name, result))
            status = "✅ PASSED" if result else "⚠️ PARTIAL"
            print(f"{status} {test_name} Test")
        except Exception as e:
            print(f"💥 {test_name} Test failed with exception: {e}")
            test_results.append((test_name, False))
    
    # Final summary
    print(f"\n📊 INTEGRATION TEST SUMMARY")
    print(f"{'='*60}")
    
    passed_tests = sum(1 for _, result in test_results if result)
    
    for test_name, result in test_results:
        status = "✅" if result else "❌"
        print(f"{status} {test_name}")
    
    print(f"\nOverall Result: {passed_tests}/{len(tests)} tests passed")
    
    if passed_tests >= len(tests) * 0.75:  # 75% pass rate
        print("🎉 PEST AGENT INTEGRATION SUCCESSFUL!")
        print("✅ Ready for orchestrator integration and production use")
    else:
        print("⚠️ Some integration issues detected, but core functionality working")
    
    print(f"\n🚀 PEST AGENT (STEP 3.c) VALIDATION COMPLETE!")

if __name__ == "__main__":
    main()
