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


class OrderState:
    """Manages the current coffee order state"""
    def __init__(self):
        self.drink_type: Optional[str] = None
        self.size: Optional[str] = None
        self.milk: Optional[str] = None
        self.extras: List[str] = []
        self.name: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "drinkType": self.drink_type,
            "size": self.size,
            "milk": self.milk,
            "extras": self.extras,
            "name": self.name
        }
    
    def is_complete(self) -> bool:
        """Check if all required fields are filled"""
        return all([
            self.drink_type is not None,
            self.size is not None,
            self.milk is not None,
            self.name is not None
        ])
    
    def get_missing_fields(self) -> List[str]:
        """Get list of missing required fields"""
        missing = []
        if not self.drink_type:
            missing.append("drink type")
        if not self.size:
            missing.append("size")
        if not self.milk:
            missing.append("milk preference")
        if not self.name:
            missing.append("name for the order")
        return missing


class Assistant(Agent):
    def __init__(self) -> None:
        # Initialize order state
        self.order = OrderState()
        
        super().__init__(
            instructions="""You are Maya, a friendly and enthusiastic barista at "The Perfect Cup" coffee shop. 
            You're passionate about coffee and love helping customers find their perfect drink!
            
            Your personality:
            - Warm, welcoming, and energetic
            - Knowledgeable about coffee drinks and options
            - Patient and helpful when customers need guidance
            - Always confirm details to ensure the order is perfect
            
            When taking orders:
            - Greet customers warmly and ask how you can help them today
            - Guide them through selecting: drink type, size, milk preference, any extras, and their name
            - Offer suggestions if they seem unsure
            - Confirm all details before completing the order
            - Keep the conversation natural and friendly
            
            Available drink types: Espresso, Americano, Latte, Cappuccino, Macchiato, Mocha, Flat White, Frappuccino, Cold Brew, Iced Coffee
            Available sizes: Small (8oz), Medium (12oz), Large (16oz), Extra Large (20oz)
            Milk options: Whole milk, 2% milk, Skim milk, Oat milk, Almond milk, Soy milk, Coconut milk, No milk
            Common extras: Extra shot, Decaf, Extra hot, Iced, Whipped cream, Extra foam, Vanilla syrup, Caramel syrup, Hazelnut syrup, Sugar-free options
            
            Your responses should be conversational and natural, as if speaking to a customer in person.
            Don't use complex formatting, just speak naturally.""",
        )

    @function_tool
    async def update_drink_type(self, context: RunContext, drink_type: str):
        """Update the customer's drink choice.
        
        Args:
            drink_type: The type of coffee drink (e.g., Latte, Cappuccino, Americano, etc.)
        """
        logger.info(f"Updating drink type to: {drink_type}")
        self.order.drink_type = drink_type
        return f"Great choice! I've got {drink_type} for your order."

    @function_tool
    async def update_size(self, context: RunContext, size: str):
        """Update the size of the customer's drink.
        
        Args:
            size: The size of the drink (Small, Medium, Large, Extra Large)
        """
        logger.info(f"Updating size to: {size}")
        self.order.size = size
        return f"Perfect! {size} size it is."

    @function_tool
    async def update_milk(self, context: RunContext, milk_type: str):
        """Update the customer's milk preference.
        
        Args:
            milk_type: Type of milk (Whole milk, Oat milk, Almond milk, etc., or No milk)
        """
        logger.info(f"Updating milk to: {milk_type}")
        self.order.milk = milk_type
        return f"Noted! {milk_type} for your drink."

    @function_tool
    async def add_extras(self, context: RunContext, extras: str):
        """Add extras or special requests to the customer's order.
        
        Args:
            extras: Extra items like syrups, extra shots, whipped cream, etc.
        """
        logger.info(f"Adding extras: {extras}")
        if extras not in self.order.extras:
            self.order.extras.append(extras)
        return f"Added {extras} to your order!"

    @function_tool
    async def update_name(self, context: RunContext, customer_name: str):
        """Record the customer's name for the order.
        
        Args:
            customer_name: The customer's name for the order
        """
        logger.info(f"Updating customer name to: {customer_name}")
        self.order.name = customer_name
        return f"Thanks {customer_name}! I've got your name for the order."

    @function_tool
    async def check_order_status(self, context: RunContext):
        """Check what's missing from the current order and provide a summary.
        """
        logger.info("Checking order status")
        missing = self.order.get_missing_fields()
        
        if not missing:
            return "Your order looks complete! Let me confirm everything with you."
        else:
            missing_str = ", ".join(missing)
            return f"I still need to get your {missing_str} to complete your order."

    @function_tool
    async def complete_order(self, context: RunContext):
        """Complete the order and save it to a JSON file.
        """
        logger.info("Attempting to complete order")
        
        if not self.order.is_complete():
            missing = self.order.get_missing_fields()
            missing_str = ", ".join(missing)
            return f"I still need your {missing_str} before I can complete your order."
        
        # Create orders directory if it doesn't exist
        orders_dir = "orders"
        if not os.path.exists(orders_dir):
            os.makedirs(orders_dir)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"order_{timestamp}_{self.order.name.replace(' ', '_').lower()}.json"
        filepath = os.path.join(orders_dir, filename)
        
        # Create order summary
        order_summary = {
            "timestamp": datetime.now().isoformat(),
            "customer": self.order.name,
            "order": self.order.to_dict(),
            "total_summary": f"{self.order.size} {self.order.drink_type} with {self.order.milk}" + 
                           (f" and {', '.join(self.order.extras)}" if self.order.extras else "")
        }
        
        # Save to JSON file
        with open(filepath, 'w') as f:
            json.dump(order_summary, f, indent=2)
        
        logger.info(f"Order saved to {filepath}")
        
        # Reset order for next customer
        self.order = OrderState()
        
        return f"Perfect! Your order has been placed and saved. Your {order_summary['total_summary']} will be ready shortly, {order_summary['customer']}! Thanks for visiting The Perfect Cup!"

    # To add tools, use the @function_tool decorator.
    # The tools are already implemented above for managing coffee orders!


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
