import logging
import json
import os
import random
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

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


class LearningState:
    """Manages the current learning session state"""
    def __init__(self):
        self.mode: Optional[str] = None  # "learn", "quiz", "teach_back"
        self.current_concept: Optional[str] = None
        self.concepts_learned: List[str] = []
        self.quiz_attempts: Dict[str, int] = {}
        self.teach_back_scores: Dict[str, List[str]] = {}  # concept_id -> list of feedback
    
    def to_dict(self) -> Dict:
        return {
            "mode": self.mode,
            "currentConcept": self.current_concept,
            "conceptsLearned": self.concepts_learned,
            "quizAttempts": self.quiz_attempts,
            "teachBackScores": self.teach_back_scores
        }


class TutorContentManager:
    """Manages the tutor content from the JSON file"""
    def __init__(self, content_file: str):
        self.content_file = content_file
        self.concepts = self._load_content()
    
    def _load_content(self) -> List[Dict]:
        """Load concepts from the JSON file"""
        try:
            content_path = Path(__file__).parent.parent / "shared-data" / self.content_file
            with open(content_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load content file {self.content_file}: {e}")
            return []
    
    def get_concept_by_id(self, concept_id: str) -> Optional[Dict]:
        """Get a specific concept by its ID"""
        return next((concept for concept in self.concepts if concept["id"] == concept_id), None)
    
    def get_all_concepts(self) -> List[Dict]:
        """Get all available concepts"""
        return self.concepts
    
    def get_random_concept(self) -> Optional[Dict]:
        """Get a random concept"""
        if not self.concepts:
            return None
        return random.choice(self.concepts)


class TutorAssistant(Agent):
    def __init__(self) -> None:
        # Initialize learning state and content manager
        self.learning_state = LearningState()
        self.content_manager = TutorContentManager("day4_tutor_content.json")
        self._current_instructions = self._get_current_instructions()
        
        super().__init__(
            instructions=self._current_instructions,
        )

    def _get_current_instructions(self) -> str:
        """Get instructions based on current learning mode"""
        base_instructions = """You are an active recall learning coach that helps users learn through teaching. The user is interacting with you via voice.
        Your responses are conversational, encouraging, and without complex formatting or symbols.
        
        You have access to function tools to switch learning modes, get concepts, and track progress.
        When users ask to switch modes or learn concepts, use the appropriate function tools.
        """
        
        if self.learning_state.mode == "learn":
            return base_instructions + """
            CURRENT MODE: LEARN - You are Matthew, the Explainer. 
            Your role is to teach concepts clearly and engagingly.
            - Explain concepts in simple, understandable terms
            - Use analogies and examples to make concepts stick
            - Keep explanations concise but thorough
            - Ask if the user wants to move to quiz mode after explaining
            """
        elif self.learning_state.mode == "quiz":
            return base_instructions + """
            CURRENT MODE: QUIZ - You are Alicia, the Quizmaster.
            Your role is to test the user's understanding.
            - Ask thoughtful questions about the concept
            - Give encouraging feedback on answers
            - Offer hints if the user struggles
            - Suggest moving to teach-back mode when they're ready
            """
        elif self.learning_state.mode == "teach_back":
            return base_instructions + """
            CURRENT MODE: TEACH BACK - You are Ken, the Evaluator.
            Your role is to listen as the user teaches you the concept.
            - Ask the user to explain the concept back to you
            - Give constructive feedback on their explanation
            - Point out what they got right and areas for improvement
            - Encourage them and suggest which concept to try next
            """
        else:
            return base_instructions + """
            You are a learning coach ready to help. When users first interact:
            1. Greet them warmly
            2. Explain the three available learning modes:
               - LEARN mode: You'll explain concepts to them (Matthew voice)
               - QUIZ mode: You'll test their understanding (Alicia voice) 
               - TEACH BACK mode: They'll teach concepts back to you (Ken voice)
            3. Ask which mode they'd prefer to start with
            4. Use the switch_learning_mode function tool when they choose
            """

    @function_tool
    async def switch_learning_mode(self, context: RunContext, mode: str, concept_id: str = None):
        """Switch to a different learning mode and optionally select a concept.
        
        Args:
            mode: The learning mode ("learn", "quiz", "teach_back")
            concept_id: Optional specific concept to focus on (variables, loops, functions, conditionals, data_types)
        """
        logger.info(f"Switching to {mode} mode with concept {concept_id}")
        
        # Validate mode
        valid_modes = ["learn", "quiz", "teach_back"]
        if mode not in valid_modes:
            return f"Invalid mode. Please choose from: {', '.join(valid_modes)}"
        
        # Set the new mode
        old_mode = self.learning_state.mode
        self.learning_state.mode = mode
        
        # Select concept
        if concept_id:
            concept = self.content_manager.get_concept_by_id(concept_id)
            if concept:
                self.learning_state.current_concept = concept_id
            else:
                available_concepts = [c["id"] for c in self.content_manager.get_all_concepts()]
                return f"Concept '{concept_id}' not found. Available concepts: {', '.join(available_concepts)}"
        elif not self.learning_state.current_concept:
            # Pick a random concept if none selected
            concept = self.content_manager.get_random_concept()
            if concept:
                self.learning_state.current_concept = concept["id"]
        
        # Update our internal instructions reference (for future sessions)
        self._current_instructions = self._get_current_instructions()
        
        # Mode-specific responses
        current_concept = self.content_manager.get_concept_by_id(self.learning_state.current_concept)
        concept_title = current_concept["title"] if current_concept else "a concept"
        
        if mode == "learn":
            response = f"Switched to LEARN mode! I'm Matthew, your explainer. Let me teach you about {concept_title}."
            if current_concept:
                response += f" {current_concept['summary']} Would you like to move to quiz mode to test your understanding?"
        elif mode == "quiz":
            response = f"Switched to QUIZ mode! I'm Alicia, your quizmaster. Let's test your knowledge of {concept_title}!"
            if current_concept:
                response += f" {current_concept['sample_question']}"
        elif mode == "teach_back":
            response = f"Switched to TEACH BACK mode! I'm Ken, your evaluator. Please explain {concept_title} back to me in your own words. I'll give you feedback on your explanation!"
        
        return response

    @function_tool
    async def get_available_concepts(self, context: RunContext):
        """Get a list of all available learning concepts."""
        concepts = self.content_manager.get_all_concepts()
        concept_list = [f"{concept['id']}: {concept['title']}" for concept in concepts]
        return f"Available concepts to learn: {', '.join(concept_list)}"

    @function_tool
    async def get_learning_progress(self, context: RunContext):
        """Get the user's current learning progress and statistics."""
        state = self.learning_state
        progress_info = [
            f"Current mode: {state.mode or 'Not set'}",
            f"Current concept: {state.current_concept or 'None selected'}",
            f"Concepts learned: {len(state.concepts_learned)}",
            f"Quiz attempts: {len(state.quiz_attempts)}",
            f"Teach-back sessions: {len(state.teach_back_scores)}"
        ]
        return " | ".join(progress_info)

    @function_tool
    async def provide_feedback(self, context: RunContext, concept_id: str, feedback_type: str, score: str):
        """Provide feedback for a teach-back session.
        
        Args:
            concept_id: The concept being taught back
            feedback_type: Type of feedback (good, needs_improvement, excellent)
            score: Qualitative score or feedback text
        """
        if concept_id not in self.learning_state.teach_back_scores:
            self.learning_state.teach_back_scores[concept_id] = []
        
        self.learning_state.teach_back_scores[concept_id].append(f"{feedback_type}: {score}")
        
        # Mark concept as learned if feedback is positive
        if feedback_type in ["good", "excellent"] and concept_id not in self.learning_state.concepts_learned:
            self.learning_state.concepts_learned.append(concept_id)
        
        return f"Feedback recorded for {concept_id}: {feedback_type} - {score}"


   
def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


async def entrypoint(ctx: JobContext):
    # Logging setup
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    # Create the tutor assistant
    tutor_assistant = TutorAssistant()

    # Function to get the appropriate voice based on learning mode
    def get_voice_for_mode(mode: str) -> str:
        voice_mapping = {
            "learn": "en-US-matthew",      # Matthew - The Explainer
            "quiz": "en-US-alicia",       # Alicia - The Quizmaster  
            "teach_back": "en-US-ken",    # Ken - The Evaluator
        }
        return voice_mapping.get(mode, "en-US-matthew")  # Default to Matthew

    # Create initial session with default voice
    session = AgentSession(
        # Speech-to-text (STT) 
        stt=deepgram.STT(model="nova-3"),
        # Large Language Model (LLM) 
        llm=google.LLM(model="gemini-2.5-flash"),
        # Text-to-speech (TTS) - will be updated based on mode
        tts=murf.TTS(
            voice=get_voice_for_mode(tutor_assistant.learning_state.mode), 
            style="Conversation",
            tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
            text_pacing=True
        ),
        # VAD and turn detection
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=True,
    )

    # Function to update TTS voice when mode changes
    async def update_voice_for_mode(new_mode: str):
        try:
            new_voice = get_voice_for_mode(new_mode)
            # Create new TTS with the appropriate voice
            new_tts = murf.TTS(
                voice=new_voice,
                style="Conversation", 
                tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
                text_pacing=True
            )
            # Update the session's TTS safely
            if hasattr(session, '_tts') and session._tts:
                session._tts = new_tts
                logger.info(f"Switched to voice: {new_voice} for mode: {new_mode}")
            else:
                logger.warning(f"Could not update voice to {new_voice}, session TTS not accessible")
        except Exception as e:
            logger.error(f"Failed to update voice for mode {new_mode}: {e}")

    # Override the switch_learning_mode function to also update voice
    original_switch_mode = tutor_assistant.switch_learning_mode

    async def enhanced_switch_mode(context: RunContext, mode: str, concept_id: str = None):
        result = await original_switch_mode(context, mode, concept_id)
        # Only try to update voice if the mode switch was successful
        if not result.startswith("Invalid mode") and not result.startswith("Concept") and "not found" not in result:
            await update_voice_for_mode(mode)
        return result

    # Replace the function tool
    tutor_assistant.switch_learning_mode = enhanced_switch_mode

    # Metrics collection
    usage_collector = metrics.UsageCollector()

    @session.on("metrics_collected")
    def _on_metrics_collected(ev: MetricsCollectedEvent):
        metrics.log_metrics(ev.metrics)
        usage_collector.collect(ev.metrics)

    async def log_usage():
        summary = usage_collector.get_summary()
        logger.info(f"Usage: {summary}")

    ctx.add_shutdown_callback(log_usage)

    # Start the session
    await session.start(
        agent=tutor_assistant,
        room=ctx.room,
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )

    # Join the room and connect to the user
    await ctx.connect()


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))
