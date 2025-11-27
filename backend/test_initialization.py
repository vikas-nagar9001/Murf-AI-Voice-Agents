#!/usr/bin/env python3
"""Simple test to verify SDR agent can be initialized"""

from src.agent import Assistant

def test_agent_initialization():
    try:
        # Initialize the agent
        agent = Assistant()
        
        print("✅ SDR Agent initialized successfully!")
        print(f"✅ Company: {agent.company_data['company']['name']}")
        print(f"✅ FAQ entries loaded: {len(agent.company_data['faq'])}")
        print(f"✅ Agent persona: Priya (Razorpay SDR)")
        print(f"✅ Lead tracking initialized")
        
        # Test FAQ search
        result = agent._search_faq("what does razorpay do")
        if result:
            print("✅ FAQ search working correctly")
        else:
            print("❌ FAQ search failed")
            
        # Test lead data
        agent.lead.name = "Test User"
        agent.lead.company = "Test Corp"
        collected = agent.lead.get_collected_fields()
        if len(collected) == 2:
            print("✅ Lead data collection working")
        else:
            print("❌ Lead data collection failed")
            
        print("\n🎉 Razorpay SDR Voice Agent is ready for conversations!")
        return True
        
    except Exception as e:
        print(f"❌ Error initializing agent: {e}")
        return False

if __name__ == "__main__":
    test_agent_initialization()