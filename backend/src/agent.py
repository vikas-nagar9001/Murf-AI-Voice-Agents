import logging
import json
import os
from datetime import datetime
from typing import Dict, List, Optional

from dotenv import load_dotenv
from fraud_database import FraudDatabase
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
from livekit.plugins import murf, silero, deepgram, noise_cancellation, openai
from livekit.plugins.turn_detector.multilingual import MultilingualModel

logger = logging.getLogger("agent")

load_dotenv(".env.local")


class FraudCaseState:
    """Manages the current fraud case state"""
    def __init__(self):
        self.current_case: Optional[Dict] = None
        self.username: Optional[str] = None
        self.verification_passed: bool = False
        self.transaction_confirmed: Optional[bool] = None
        self.call_complete: bool = False
        
    def set_case(self, case: Dict):
        """Set the current fraud case"""
        self.current_case = case
        self.username = case.get('user_name')
        
    def is_verified(self) -> bool:
        """Check if customer verification has passed"""
        return self.verification_passed
        
    def is_complete(self) -> bool:
        """Check if the fraud investigation is complete"""
        return self.call_complete
        
    def get_transaction_summary(self) -> str:
        """Get a formatted summary of the suspicious transaction"""
        if not self.current_case:
            return "No transaction data available"
            
        case = self.current_case
        return f"""A transaction of ${case['transaction_amount']} at {case['transaction_name']} from {case['transaction_source']} in {case['transaction_location']} on {case['transaction_time']} using your card ending in {case['card_ending']}"""


class Assistant(Agent):
    def __init__(self) -> None:
        # Initialize fraud case state and database
        self.fraud_state = FraudCaseState()
        self.fraud_db = FraudDatabase()
        
        super().__init__(
            instructions="""You are a professional fraud detection representative for SecureBank. You are calling customers about suspicious transactions on their accounts.
            
            Your role:
            - Introduce yourself as calling from SecureBank's fraud department
            - Verify the customer's identity using security questions
            - Read out suspicious transaction details
            - Ask if they made the transaction
            - Take appropriate action based on their response
            
            Your tone should be:
            - Professional and reassuring
            - Clear and easy to understand
            - Calm and helpful
            - Never ask for sensitive information like full card numbers or PINs
            
            The user is interacting with you via voice, so keep responses concise and conversational without complex formatting.""",
        )

    @function_tool
    async def get_security_question(self, context: RunContext):
        """Get the security question for the current customer to verify their identity.
        
        Use this after loading a fraud case to ask the customer their security question.
        """
        if not self.fraud_state.current_case:
            return "No fraud case loaded. Please ask for the customer's name first."
            
        question = self.fraud_state.current_case['security_question']
        logger.info(f"Asking security question: {question}")
        return f"For security purposes, I need to verify your identity. {question}"
    
    @function_tool
    async def get_transaction_details(self, context: RunContext):
        """Get the details of the suspicious transaction to read to the customer.
        
        Use this after customer verification passes to provide transaction details.
        """
        if not self.fraud_state.current_case:
            return "No fraud case available."
            
        if not self.fraud_state.verification_passed:
            return "Customer identity must be verified before sharing transaction details."
            
        summary = self.fraud_state.get_transaction_summary()
        logger.info("Providing transaction details to verified customer")
        return f"Here are the details of the suspicious transaction: {summary}"

    @function_tool
    async def load_fraud_case(self, context: RunContext, username: str):
        """Load a pending fraud case for the specified username.
        
        Use this when the customer provides their name to look up their fraud case.
        
        Args:
            username: The customer's name to search for fraud cases
        """
        logger.info(f"Loading fraud case for username: {username}")
        
        case = self.fraud_db.get_fraud_case_by_username(username)
        
        if case:
            self.fraud_state.set_case(case)
            logger.info(f"Loaded fraud case ID {case['id']} for {username}")
            return f"Found a fraud alert for {username}. I can see a suspicious transaction on your account."
        else:
            logger.info(f"No pending fraud cases found for {username}")
            return f"I don't see any pending fraud alerts for {username}. You may have the wrong department."
    
    @function_tool
    async def verify_customer(self, context: RunContext, security_answer: str):
        """Verify the customer's identity using their security answer.
        
        Use this after asking the customer their security question to verify their identity.
        
        Args:
            security_answer: The customer's answer to the security question
        """
        if not self.fraud_state.current_case:
            return "No fraud case loaded. Please provide your name first."
            
        expected_answer = self.fraud_state.current_case['security_answer'].lower()
        provided_answer = security_answer.lower().strip()
        
        logger.info(f"Verifying customer identity")
        
        if expected_answer == provided_answer:
            self.fraud_state.verification_passed = True
            logger.info("Customer verification passed")
            return "Thank you for verifying your identity. Now let me tell you about the suspicious transaction."
        else:
            logger.info("Customer verification failed")
            return "I'm sorry, but that answer doesn't match our records. For your security, I cannot proceed with this call."
    
    @function_tool
    async def confirm_transaction(self, context: RunContext, user_made_transaction: bool):
        """Record whether the customer confirmed or denied making the suspicious transaction.
        
        Use this after the customer responds yes or no to whether they made the transaction.
        
        Args:
            user_made_transaction: True if customer confirmed they made the transaction, False if they denied it
        """
        if not self.fraud_state.current_case or not self.fraud_state.verification_passed:
            return "Cannot process transaction confirmation. Customer must be verified first."
            
        case = self.fraud_state.current_case
        self.fraud_state.transaction_confirmed = user_made_transaction
        
        if user_made_transaction:
            # Customer confirmed the transaction is legitimate
            success = self.fraud_db.update_case_status(
                case['id'], 
                'confirmed_safe',
                'Customer confirmed transaction as legitimate'
            )
            self.fraud_state.call_complete = True
            
            if success:
                logger.info(f"Case {case['id']} marked as safe")
                return "Perfect! I've updated your account to show this transaction is legitimate. No further action is needed. Thank you for your time."
            else:
                return "I've noted that you confirmed the transaction, though there was a technical issue updating our records. Your account is safe."
                
        else:
            # Customer denied making the transaction - it's fraud
            success = self.fraud_db.update_case_status(
                case['id'], 
                'confirmed_fraud',
                'Customer denied making transaction - card blocked and dispute initiated'
            )
            self.fraud_state.call_complete = True
            
            if success:
                logger.info(f"Case {case['id']} marked as fraud")
                return f"I understand this transaction is fraudulent. I've immediately blocked your card ending in {case['card_ending']} and initiated a dispute. You'll receive a new card within 3-5 business days. Is there anything else I can help you with regarding this matter?"
            else:
                return "I've noted this as a fraudulent transaction. Your card will be blocked shortly and a dispute will be initiated."


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
        llm=openai.LLM(
                model="gpt-4o-mini",
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
