import logging
import json
import os
from datetime import datetime
from typing import Dict, List, Optional

from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    JobProcess,
    MetricsCollectedEvent,
    RoomInputOptions,
    WorkerOptions,
    cli,
    metrics,
    tokenize,
    function_tool,
    RunContext
)
from livekit.plugins import murf, silero, google, deepgram, noise_cancellation
from livekit.plugins.turn_detector.multilingual import MultilingualModel

logger = logging.getLogger("agent")

load_dotenv(".env.local")


class LeadData:
    """Manages the current lead information"""
    def __init__(self):
        self.name: Optional[str] = None
        self.company: Optional[str] = None
        self.email: Optional[str] = None
        self.role: Optional[str] = None
        self.use_case: Optional[str] = None
        self.team_size: Optional[str] = None
        self.timeline: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "company": self.company,
            "email": self.email,
            "role": self.role,
            "use_case": self.use_case,
            "team_size": self.team_size,
            "timeline": self.timeline,
            "collected_at": datetime.now().isoformat()
        }
    
    def get_collected_fields(self) -> List[str]:
        """Get list of fields that have been collected"""
        collected = []
        if self.name: collected.append("name")
        if self.company: collected.append("company")
        if self.email: collected.append("email")
        if self.role: collected.append("role")
        if self.use_case: collected.append("use case")
        if self.team_size: collected.append("team size")
        if self.timeline: collected.append("timeline")
        return collected


class Assistant(Agent):
    def __init__(self) -> None:
        # Load company data
        self.company_data = self._load_company_data()
        
        # Initialize lead state
        self.lead = LeadData()
        self.conversation_stage = "greeting"  # greeting, qualifying, collecting_info, closing
        
        super().__init__(
            instructions=f"""You are Priya, a friendly and professional Sales Development Representative (SDR) for Razorpay, India's leading payments platform. 

Your role is to:
1. Greet visitors warmly and ask what brought them here
2. Understand their business needs and payment challenges
3. Answer questions about Razorpay using the company knowledge you have
4. Naturally collect lead information during the conversation
5. Provide value and build trust before asking for contact details

Key guidelines:
- Be conversational, helpful, and professional
- Ask one question at a time to avoid overwhelming the prospect
- Listen actively and respond to their specific needs
- Use the FAQ knowledge to answer product questions accurately
- Don't make up information not in the company data
- Naturally weave in lead qualification questions during the conversation
- Keep responses concise and avoid complex formatting
- When you sense the conversation is ending, provide a summary

Company: {self.company_data['company']['name']}
What we do: {self.company_data['company']['description']}

Your responses should be natural, conversational, and focused on understanding the prospect's business needs."""
        )
    
    
    def _search_faq(self, query: str) -> Optional[str]:
        """Search FAQ for relevant answers using keyword matching"""
        query_lower = query.lower()
        
        # Keywords for different topics
        keyword_matches = {
            "what": ["what does", "what do you", "what is"],
            "pricing": ["price", "cost", "fee", "charge", "pricing", "how much"],
            "free": ["free", "trial", "no cost"],
            "who": ["who is this for", "target", "customer"],
            "payment methods": ["payment method", "upi", "card", "netbanking", "wallet"],
            "settlement": ["money", "settlement", "payout", "receive"],
            "security": ["safe", "secure", "security", "fraud"],
            "integration": ["integrate", "setup", "install", "api"],
            "support": ["support", "help", "customer service"],
            "international": ["international", "global", "foreign", "worldwide"],
            "banking": ["business banking", "razorpayx", "current account"],
            "onboarding": ["onboard", "setup time", "how long"]
        }
        
        # Find matching FAQs
        for faq in self.company_data.get("faq", []):
            question_lower = faq["question"].lower()
            answer_lower = faq["answer"].lower()
            
            # Check if query matches question or if keywords match
            if query_lower in question_lower or question_lower in query_lower:
                return faq["answer"]
            
            # Check keyword matches
            for topic, keywords in keyword_matches.items():
                if any(keyword in query_lower for keyword in keywords):
                    if topic == "what" and any(word in question_lower for word in ["what does", "what is"]):
                        return faq["answer"]
                    elif topic in question_lower or topic in answer_lower:
                        return faq["answer"]
        
        return None
    
    def _save_lead_data(self):
        """Save lead data to JSON file"""
        try:
            leads_dir = "leads"
            if not os.path.exists(leads_dir):
                os.makedirs(leads_dir)
            
            filename = f"{leads_dir}/lead_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, "w") as f:
                json.dump(self.lead.to_dict(), f, indent=2)
            
            logger.info(f"Lead data saved to {filename}")
            return filename
        except Exception as e:
            logger.error(f"Failed to save lead data: {e}")
            return None

    @function_tool
    async def answer_product_question(self, context: RunContext, question: str):
        """Use this tool to answer questions about Razorpay's products, pricing, or services.
        
        This tool searches the FAQ database for relevant information to answer user questions
        about what Razorpay does, pricing, features, integrations, etc.
        
        Args:
            question: The user's question about Razorpay's products or services
        """
        
        logger.info(f"Searching FAQ for: {question}")
        
        answer = self._search_faq(question)
        
        if answer:
            return f"Based on our company information: {answer}"
        else:
            return "I don't have specific information about that in my knowledge base. Let me connect you with someone who can provide more detailed information. Could you share your email so we can follow up with you?"

    @function_tool
    async def collect_lead_info(self, context: RunContext, field: str, value: str):
        """Use this tool to store lead information as you collect it during the conversation.
        
        Call this tool whenever the user provides information about themselves or their business
        that would be valuable for follow-up.
        
        Args:
            field: The type of information being collected (name, company, email, role, use_case, team_size, timeline)
            value: The information provided by the user
        """
        
        logger.info(f"Collecting lead info - {field}: {value}")
        
        field_lower = field.lower()
        
        if "name" in field_lower:
            self.lead.name = value
        elif "company" in field_lower or "business" in field_lower:
            self.lead.company = value
        elif "email" in field_lower:
            self.lead.email = value
        elif "role" in field_lower or "position" in field_lower or "title" in field_lower:
            self.lead.role = value
        elif "use" in field_lower or "case" in field_lower or "need" in field_lower:
            self.lead.use_case = value
        elif "team" in field_lower or "size" in field_lower:
            self.lead.team_size = value
        elif "time" in field_lower or "timeline" in field_lower or "when" in field_lower:
            self.lead.timeline = value
        
        collected_fields = self.lead.get_collected_fields()
        return f"Got it! I've noted down your {field}. So far I have: {', '.join(collected_fields)}"

    @function_tool
    async def generate_call_summary(self, context: RunContext):
        """Use this tool when the conversation is ending to create a summary and save the lead data.
        
        Call this when the user indicates they're done, says goodbye, or asks to end the conversation.
        This will create both a verbal summary and save the collected lead information to a file.
        """
        
        logger.info("Generating call summary and saving lead data")
        
        # Save lead data to file
        filename = self._save_lead_data()
        
        # Create summary
        collected_fields = self.lead.get_collected_fields()
        
        if collected_fields:
            summary = f"Perfect! Let me summarize what we discussed today. "
            
            if self.lead.name:
                summary += f"I spoke with {self.lead.name}"
                if self.lead.company:
                    summary += f" from {self.lead.company}"
                summary += ". "
            
            if self.lead.use_case:
                summary += f"You're looking to {self.lead.use_case}. "
            
            if self.lead.timeline:
                summary += f"Your timeline is {self.lead.timeline}. "
            
            if self.lead.team_size:
                summary += f"You mentioned working with a team of {self.lead.team_size}. "
            
            summary += f"I've saved all your information and someone from our team will follow up with you soon. Thank you for your time today!"
            
        else:
            summary = "Thank you for learning about Razorpay today! Even though we didn't collect detailed contact information, I hope our conversation was helpful. Feel free to reach out anytime if you have more questions about our payment solutions."
        
        return summary

    def _load_company_data(self) -> Dict:
        """Load company data from JSON file"""
        try:
            with open("src/company_data.json", "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load company data: {e}")
            return {}


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


async def entrypoint(ctx: JobContext):
    # Logging setup
    # Add any other context you want in all log entries here
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    # Set up a voice AI pipeline optimized for SDR conversations
    session = AgentSession(
        # Speech-to-text (STT) - using Deepgram for accurate transcription
        stt=deepgram.STT(model="nova-3"),
        # Large Language Model (LLM) - using Google Gemini for intelligent responses
        llm=google.LLM(
                model="gemini-2.5-flash",
            ),
        # Text-to-speech (TTS) - using Murf with Indian English voice for authenticity
        tts=murf.TTS(
                voice="en-IN-priya", 
                style="Conversation",
                tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
                text_pacing=True
            ),
        # VAD and turn detection for smooth conversation flow
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        # Allow LLM to generate responses while waiting for end of turn for natural conversation
        preemptive_generation=True,
    )

    # Metrics collection for performance monitoring
    usage_collector = metrics.UsageCollector()

    @session.on("metrics_collected")
    def _on_metrics_collected(ev: MetricsCollectedEvent):
        metrics.log_metrics(ev.metrics)
        usage_collector.collect(ev.metrics)

    async def log_usage():
        summary = usage_collector.get_summary()
        logger.info(f"Usage: {summary}")

    ctx.add_shutdown_callback(log_usage)

    # Start the session with our SDR Assistant
    await session.start(
        agent=Assistant(),
        room=ctx.room,
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )

    # Join the room and connect to the user
    await ctx.connect()


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))
