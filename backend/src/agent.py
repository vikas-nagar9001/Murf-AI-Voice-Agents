import logging
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any

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


class WellnessData:
    """Manages daily wellness check-in data"""
    def __init__(self):
        self.today_mood: Optional[str] = None
        self.today_energy: Optional[str] = None
        self.today_stress: Optional[str] = None
        self.today_objectives: List[str] = []
        self.check_in_complete: bool = False
        self.wellness_file = "wellness_log.json"
    
    def load_previous_entries(self) -> List[Dict]:
        """Load previous wellness entries from JSON file"""
        if os.path.exists(self.wellness_file):
            try:
                with open(self.wellness_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                return []
        return []
    
    def get_recent_entry(self) -> Optional[Dict]:
        """Get the most recent wellness entry"""
        entries = self.load_previous_entries()
        return entries[-1] if entries else None
    
    def save_today_entry(self) -> str:
        """Save today's wellness check-in to JSON file"""
        entries = self.load_previous_entries()
        
        today_entry = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "timestamp": datetime.now().isoformat(),
            "mood": self.today_mood,
            "energy_level": self.today_energy,
            "stress_level": self.today_stress,
            "daily_objectives": self.today_objectives,
            "summary": self.generate_summary()
        }
        
        entries.append(today_entry)
        
        with open(self.wellness_file, 'w') as f:
            json.dump(entries, f, indent=2)
        
        return f"wellness check-in saved for {today_entry['date']}"
    
    def generate_summary(self) -> str:
        """Generate a brief summary of today's check-in"""
        mood_part = f"feeling {self.today_mood}" if self.today_mood else "mood noted"
        energy_part = f"with {self.today_energy} energy" if self.today_energy else ""
        objectives_count = len(self.today_objectives)
        
        summary = f"User reported {mood_part}"
        if energy_part:
            summary += f" {energy_part}"
        if objectives_count > 0:
            summary += f" and set {objectives_count} objective{'s' if objectives_count != 1 else ''} for the day"
        
        return summary
    
    def is_ready_for_completion(self) -> bool:
        """Check if we have enough info to complete the check-in"""
        return (self.today_mood is not None and 
                self.today_energy is not None and 
                len(self.today_objectives) > 0)


class Assistant(Agent):
    def __init__(self) -> None:
        # Initialize wellness tracking
        self.wellness = WellnessData()
        
        super().__init__(
            instructions="""You are Alex, a supportive and grounded wellness companion. You help people with daily check-ins about their mental and physical well-being.
            
            Your role:
            - Conduct brief, supportive daily wellness check-ins
            - Ask about mood, energy levels, and daily intentions
            - Offer practical, small-step advice (never medical advice)
            - Reference previous check-ins to show continuity
            - Help users stay grounded and realistic about their goals
            
            Your personality:
            - Warm but not overly enthusiastic
            - Realistic and practical
            - Non-judgmental and supportive
            - Grounded in evidence-based wellness practices
            - Never diagnose or provide medical advice
            
            Check-in flow:
            1. Greet warmly and reference previous sessions if available
            2. Ask about today's mood and energy
            3. Inquire about stress or concerns
            4. Discuss 1-3 realistic daily objectives
            5. Offer simple, actionable suggestions
            6. Recap and confirm understanding
            
            Keep responses conversational and natural. Avoid clinical language or complex formatting.
            Focus on small, achievable steps that can improve someone's day.""",
        )

    @function_tool
    async def get_previous_context(self, context: RunContext) -> str:
        """Retrieve information from previous wellness check-ins to provide context."""
        logger.info("Retrieving previous wellness context")
        recent_entry = self.wellness.get_recent_entry()
        
        if recent_entry:
            date = recent_entry.get('date', 'recently')
            mood = recent_entry.get('mood', '')
            energy = recent_entry.get('energy_level', '')
            objectives_count = len(recent_entry.get('daily_objectives', []))
            
            context_message = f"Last time we checked in on {date}, you mentioned feeling {mood}"
            if energy:
                context_message += f" with {energy} energy levels"
            if objectives_count > 0:
                context_message += f" and you had {objectives_count} goals for that day"
            
            return context_message + ". How does today compare?"
        else:
            return "This seems to be our first check-in together! I'm here to help you reflect on your day and set some positive intentions."

    @function_tool
    async def record_mood(self, context: RunContext, mood_description: str) -> str:
        """Record the user's current mood or emotional state.
        
        Args:
            mood_description: How the user is feeling today (e.g., 'good', 'stressed', 'calm', 'overwhelmed', etc.)
        """
        logger.info(f"Recording mood: {mood_description}")
        self.wellness.today_mood = mood_description
        return f"Thanks for sharing. I've noted that you're feeling {mood_description} today."

    @function_tool
    async def record_energy_level(self, context: RunContext, energy_description: str) -> str:
        """Record the user's current energy level.
        
        Args:
            energy_description: User's energy level (e.g., 'high', 'low', 'moderate', 'tired', 'energetic', etc.)
        """
        logger.info(f"Recording energy level: {energy_description}")
        self.wellness.today_energy = energy_description
        return f"Got it. Your energy level today is {energy_description}."

    @function_tool
    async def record_stress_concerns(self, context: RunContext, stress_description: str) -> str:
        """Record any stress factors or concerns the user mentions.
        
        Args:
            stress_description: What's causing stress or concern (e.g., 'work deadline', 'none today', 'family issues', etc.)
        """
        logger.info(f"Recording stress/concerns: {stress_description}")
        self.wellness.today_stress = stress_description
        return f"I understand. I've noted that {stress_description} regarding stress today."

    @function_tool
    async def add_daily_objective(self, context: RunContext, objective: str) -> str:
        """Add a daily goal or objective that the user wants to accomplish.
        
        Args:
            objective: A specific goal or task for today (e.g., 'take a 20-minute walk', 'finish project report', etc.)
        """
        logger.info(f"Adding daily objective: {objective}")
        if objective not in self.wellness.today_objectives:
            self.wellness.today_objectives.append(objective)
        
        count = len(self.wellness.today_objectives)
        return f"Great! I've added '{objective}' to your objectives. You now have {count} goal{'s' if count != 1 else ''} for today."

    @function_tool
    async def provide_wellness_suggestion(self, context: RunContext, situation: str) -> str:
        """Provide a practical, grounded wellness suggestion based on the user's situation.
        
        Args:
            situation: Brief description of what the user might need support with
        """
        logger.info(f"Providing wellness suggestion for: {situation}")
        
        suggestions = {
            "low_energy": "Consider taking a 5-10 minute walk outside, or try some gentle stretching. Even small movement can help boost energy naturally.",
            "stressed": "Try the 4-7-8 breathing technique: breathe in for 4, hold for 7, exhale for 8. Just a few cycles can help calm your nervous system.",
            "overwhelmed": "Break your biggest task into 3 smaller steps. Focus on just the first step for now. You don't have to tackle everything at once.",
            "unfocused": "Try the Pomodoro technique: 25 minutes of focused work followed by a 5-minute break. Set a timer and commit to just one task.",
            "tired": "If possible, consider a 10-20 minute power nap, or simply rest your eyes and practice deep breathing for a few minutes.",
            "anxious": "Ground yourself with the 5-4-3-2-1 technique: notice 5 things you can see, 4 you can touch, 3 you can hear, 2 you can smell, 1 you can taste.",
            "general": "Remember to stay hydrated, take breaks when you need them, and be kind to yourself today. Small consistent actions often matter more than big gestures."
        }
        
        # Simple keyword matching for suggestions
        situation_lower = situation.lower()
        if any(word in situation_lower for word in ['tired', 'energy', 'sleepy']):
            return suggestions["low_energy"]
        elif any(word in situation_lower for word in ['stress', 'pressure', 'deadline']):
            return suggestions["stressed"]
        elif any(word in situation_lower for word in ['overwhelm', 'too much', 'busy']):
            return suggestions["overwhelmed"]
        elif any(word in situation_lower for word in ['focus', 'concentrate', 'distract']):
            return suggestions["unfocused"]
        elif any(word in situation_lower for word in ['anxious', 'worry', 'nervous']):
            return suggestions["anxious"]
        else:
            return suggestions["general"]

    @function_tool
    async def complete_wellness_checkin(self, context: RunContext) -> str:
        """Complete today's wellness check-in and save the data."""
        logger.info("Attempting to complete wellness check-in")
        
        if not self.wellness.is_ready_for_completion():
            missing = []
            if not self.wellness.today_mood:
                missing.append("mood")
            if not self.wellness.today_energy:
                missing.append("energy level")
            if len(self.wellness.today_objectives) == 0:
                missing.append("daily objectives")
            
            return f"Let me make sure I have everything. I still need to know about your {' and '.join(missing)} before we finish today's check-in."
        
        # Save the check-in
        save_result = self.wellness.save_today_entry()
        
        # Create summary
        objectives_list = ", ".join(self.wellness.today_objectives)
        summary = f"Let me recap today's check-in. You're feeling {self.wellness.today_mood} with {self.wellness.today_energy} energy levels."
        
        if self.wellness.today_stress:
            summary += f" Regarding stress, {self.wellness.today_stress}."
        
        summary += f" Your main objectives for today are: {objectives_list}. Does this sound right?"
        
        # Reset for next session
        self.wellness = WellnessData()
        
        logger.info(save_result)
        return summary + " Your check-in has been saved, and I'm here whenever you need support today!"

    # To add tools, use the @function_tool decorator.


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


async def entrypoint(ctx: JobContext):
    # Logging setup
    # Add any other context you want in all log entries here
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    # Set up a voice AI pipeline using OpenAI, Cartesia, AssemblyAI, and the LiveKit turn detector
    session = AgentSession(
        # Speech-to-text (STT) is your agent's ears, turning the user's speech into text that the LLM can understand
        # See all available models at https://docs.livekit.io/agents/models/stt/
        stt=deepgram.STT(model="nova-3"),
        # A Large Language Model (LLM) is your agent's brain, processing user input and generating a response
        # See all available models at https://docs.livekit.io/agents/models/llm/
        llm=google.LLM(
                model="gemini-2.5-flash",
            ),
        # Text-to-speech (TTS) is your agent's voice, turning the LLM's text into speech that the user can hear
        # See all available models as well as voice selections at https://docs.livekit.io/agents/models/tts/
        tts=murf.TTS(
                voice="en-US-matthew", 
                style="Conversation",
                tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
                text_pacing=True
            ),
        # VAD and turn detection are used to determine when the user is speaking and when the agent should respond
        # See more at https://docs.livekit.io/agents/build/turns
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        # allow the LLM to generate a response while waiting for the end of turn
        # See more at https://docs.livekit.io/agents/build/audio/#preemptive-generation
        preemptive_generation=True,
    )

    # To use a realtime model instead of a voice pipeline, use the following session setup instead.
    # (Note: This is for the OpenAI Realtime API. For other providers, see https://docs.livekit.io/agents/models/realtime/))
    # 1. Install livekit-agents[openai]
    # 2. Set OPENAI_API_KEY in .env.local
    # 3. Add `from livekit.plugins import openai` to the top of this file
    # 4. Use the following session setup instead of the version above
    # session = AgentSession(
    #     llm=openai.realtime.RealtimeModel(voice="marin")
    # )

    # Metrics collection, to measure pipeline performance
    # For more information, see https://docs.livekit.io/agents/build/metrics/
    usage_collector = metrics.UsageCollector()

    @session.on("metrics_collected")
    def _on_metrics_collected(ev: MetricsCollectedEvent):
        metrics.log_metrics(ev.metrics)
        usage_collector.collect(ev.metrics)

    async def log_usage():
        summary = usage_collector.get_summary()
        logger.info(f"Usage: {summary}")

    ctx.add_shutdown_callback(log_usage)

    # # Add a virtual avatar to the session, if desired
    # # For other providers, see https://docs.livekit.io/agents/models/avatar/
    # avatar = hedra.AvatarSession(
    #   avatar_id="...",  # See https://docs.livekit.io/agents/models/avatar/plugins/hedra
    # )
    # # Start the avatar and wait for it to join
    # await avatar.start(session, room=ctx.room)

    # Start the session, which initializes the voice pipeline and warms up the models
    await session.start(
        agent=Assistant(),
        room=ctx.room,
        room_input_options=RoomInputOptions(
            # For telephony applications, use `BVCTelephony` for best results
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )

    # Join the room and connect to the user
    await ctx.connect()


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))
