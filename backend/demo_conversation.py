#!/usr/bin/env python3
"""
Demonstration of the Razorpay SDR Voice Agent Workflow
This script simulates a complete conversation flow to show how the agent works.
"""

from src.agent import Assistant
import asyncio
from unittest.mock import Mock

class MockRunContext:
    """Mock context for testing function tools"""
    pass

async def simulate_conversation():
    """Simulate a complete SDR conversation workflow"""
    
    print("🎭 Razorpay SDR Voice Agent - Conversation Simulation")
    print("=" * 60)
    
    # Initialize the agent
    agent = Assistant()
    context = MockRunContext()
    
    print("\n🤖 Agent: Hi! I'm Priya from Razorpay. What brought you here today?")
    print("👤 User: Hi, I'm looking for a payment solution for my online business.")
    
    # Collect initial lead info
    await agent.collect_lead_info(context, "use_case", "payment solution for online business")
    
    print("\n🤖 Agent: That's great! We help many online businesses accept payments easily.")
    print("          What's your name and what kind of business do you run?")
    print("👤 User: I'm Kavya and I run an online clothing store called StyleHub.")
    
    # Collect more lead info
    await agent.collect_lead_info(context, "name", "Kavya")
    await agent.collect_lead_info(context, "company", "StyleHub")
    await agent.collect_lead_info(context, "use_case", "online clothing store payment processing")
    
    print("\n🤖 Agent: Nice to meet you Kavya! StyleHub sounds interesting.")
    print("          What payment challenges are you currently facing?")
    print("👤 User: Well, customers abandon carts because we only accept cards.")
    print("          Do you support UPI and other payment methods?")
    
    # Answer product question
    answer = await agent.answer_product_question(context, "what payment methods do you support")
    print(f"\n🤖 Agent: {answer}")
    
    print("\n👤 User: That's perfect! What about pricing? How much do you charge?")
    
    # Answer pricing question  
    pricing_answer = await agent.answer_product_question(context, "what are your fees and pricing")
    print(f"\n🤖 Agent: {pricing_answer}")
    
    print("\n👤 User: That sounds reasonable. I'd like to learn more about integration.")
    print("          What's your email so we can discuss further?")
    print("👤 User: My email is kavya@stylehub.in")
    
    # Collect contact info
    await agent.collect_lead_info(context, "email", "kavya@stylehub.in")
    
    print("\n🤖 Agent: Perfect! Just a couple more questions to help our team prepare.")
    print("          What's your role at StyleHub?")
    print("👤 User: I'm the founder and CEO.")
    
    await agent.collect_lead_info(context, "role", "Founder and CEO")
    
    print("\n🤖 Agent: How big is your team currently?")
    print("👤 User: We're a team of 6 people right now.")
    
    await agent.collect_lead_info(context, "team_size", "6 people")
    
    print("\n🤖 Agent: And what's your timeline for implementing a new payment solution?")
    print("👤 User: We'd like to get this set up within the next month.")
    
    await agent.collect_lead_info(context, "timeline", "within the next month")
    
    print("\n👤 User: That's all my questions for now. Thanks for the information!")
    
    # Generate call summary
    summary = await agent.generate_call_summary(context)
    print(f"\n🤖 Agent: {summary}")
    
    # Show collected lead data
    print("\n📊 LEAD DATA COLLECTED:")
    print("=" * 30)
    lead_data = agent.lead.to_dict()
    for key, value in lead_data.items():
        if key != 'collected_at' and value:
            print(f"• {key.replace('_', ' ').title()}: {value}")
    
    # Show lead qualification insights
    print("\n🎯 LEAD QUALIFICATION INSIGHTS:")
    print("=" * 35)
    
    # Check against ideal customer profile
    ideal_indicators = agent.company_data['lead_qualification']['ideal_customers']
    key_indicators = agent.company_data['lead_qualification']['key_indicators']
    
    print("✅ Ideal Customer Match:")
    if agent.lead.use_case and "clothing" in agent.lead.use_case.lower():
        print("  • E-commerce business (clothing store) ✓")
    if agent.lead.timeline and "month" in agent.lead.timeline.lower():
        print("  • Active timeline (next month) ✓")
    if agent.lead.role and "founder" in agent.lead.role.lower():
        print("  • Decision maker (Founder/CEO) ✓")
    
    print("\n🏆 QUALIFICATION SCORE: HIGH")
    print("💼 RECOMMENDED ACTION: Priority follow-up within 24 hours")
    print("📈 EXPECTED DEAL SIZE: ₹15,000-50,000 monthly GMV")
    
    print("\n" + "=" * 60)
    print("🎉 SDR Conversation Completed Successfully!")
    print("   Lead qualified and ready for Account Executive handoff")

if __name__ == "__main__":
    asyncio.run(simulate_conversation())