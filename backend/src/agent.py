import logging
import json
import os
import sys
import asyncio
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

# Fix for Windows: aiodns requires SelectorEventLoop
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

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

# Get the directory where this script is located
SCRIPT_DIR = Path(__file__).parent

# Load catalog and recipes at module level
def load_catalog() -> Dict:
    """Load the product catalog from JSON file"""
    catalog_path = SCRIPT_DIR / "catalog.json"
    with open(catalog_path, "r") as f:
        return json.load(f)

def load_recipes() -> Dict:
    """Load the recipes/ingredients mapping from JSON file"""
    recipes_path = SCRIPT_DIR / "recipes.json"
    with open(recipes_path, "r") as f:
        return json.load(f)

CATALOG = load_catalog()
RECIPES = load_recipes()


class CartItem:
    """Represents an item in the shopping cart"""
    def __init__(self, item_id: str, name: str, price: float, quantity: int = 1, notes: str = ""):
        self.item_id = item_id
        self.name = name
        self.price = price
        self.quantity = quantity
        self.notes = notes
    
    def to_dict(self) -> Dict:
        return {
            "item_id": self.item_id,
            "name": self.name,
            "price": self.price,
            "quantity": self.quantity,
            "notes": self.notes,
            "subtotal": round(self.price * self.quantity, 2)
        }


class ShoppingCart:
    """Manages the shopping cart state"""
    def __init__(self):
        self.items: Dict[str, CartItem] = {}
        self.customer_name: Optional[str] = None
        self.customer_address: Optional[str] = None
    
    def add_item(self, item_id: str, name: str, price: float, quantity: int = 1, notes: str = "") -> str:
        """Add an item to the cart or update quantity if already exists"""
        if item_id in self.items:
            self.items[item_id].quantity += quantity
            if notes:
                self.items[item_id].notes = notes
            return f"Updated {name} quantity to {self.items[item_id].quantity}"
        else:
            self.items[item_id] = CartItem(item_id, name, price, quantity, notes)
            return f"Added {quantity} {name} to your cart"
    
    def remove_item(self, item_id: str) -> str:
        """Remove an item from the cart"""
        if item_id in self.items:
            name = self.items[item_id].name
            del self.items[item_id]
            return f"Removed {name} from your cart"
        return "Item not found in cart"
    
    def update_quantity(self, item_id: str, quantity: int) -> str:
        """Update the quantity of an item"""
        if item_id in self.items:
            if quantity <= 0:
                return self.remove_item(item_id)
            self.items[item_id].quantity = quantity
            return f"Updated {self.items[item_id].name} quantity to {quantity}"
        return "Item not found in cart"
    
    def get_cart_summary(self) -> str:
        """Get a human-readable cart summary"""
        if not self.items:
            return "Your cart is empty."
        
        lines = ["Here's what's in your cart:"]
        total = 0
        for item in self.items.values():
            subtotal = item.price * item.quantity
            total += subtotal
            note_str = f" ({item.notes})" if item.notes else ""
            lines.append(f"- {item.quantity}x {item.name}{note_str}: ${subtotal:.2f}")
        
        lines.append(f"\nTotal: ${total:.2f}")
        return "\n".join(lines)
    
    def get_total(self) -> float:
        """Calculate cart total"""
        return round(sum(item.price * item.quantity for item in self.items.values()), 2)
    
    def to_dict(self) -> Dict:
        """Convert cart to dictionary for JSON serialization"""
        return {
            "items": [item.to_dict() for item in self.items.values()],
            "total": self.get_total(),
            "customer_name": self.customer_name,
            "customer_address": self.customer_address
        }
    
    def clear(self):
        """Clear all items from cart"""
        self.items.clear()


def find_item_in_catalog(search_term: str) -> Optional[Dict]:
    """Search for an item in the catalog by name or id"""
    search_lower = search_term.lower()
    
    for category, items in CATALOG["catalog"].items():
        for item in items:
            # Check by ID
            if item["id"].lower() == search_lower:
                return item
            # Check by name (partial match)
            if search_lower in item["name"].lower():
                return item
            # Check by tags
            if any(search_lower in tag.lower() for tag in item.get("tags", [])):
                return item
    return None


def find_recipe(search_term: str) -> Optional[Dict]:
    """Search for a recipe by name or alias"""
    search_lower = search_term.lower()
    
    for recipe_id, recipe in RECIPES["recipes"].items():
        # Check by recipe ID
        if search_lower in recipe_id.lower():
            return recipe
        # Check by recipe name
        if search_lower in recipe["name"].lower():
            return recipe
        # Check by aliases
        if any(search_lower in alias.lower() for alias in recipe.get("aliases", [])):
            return recipe
    return None


def get_catalog_summary() -> str:
    """Get a summary of available items in the catalog"""
    lines = ["Here's what we have available:"]
    
    for category, items in CATALOG["catalog"].items():
        category_name = category.replace("_", " ").title()
        lines.append(f"\n{category_name}:")
        for item in items:
            lines.append(f"  - {item['name']}: ${item['price']:.2f}")
    
    return "\n".join(lines)


class FoodOrderingAssistant(Agent):
    def __init__(self) -> None:
        self.cart = ShoppingCart()
        
        # Get catalog items for context
        catalog_items = []
        for category, items in CATALOG["catalog"].items():
            for item in items:
                catalog_items.append(f"{item['name']} (${item['price']:.2f})")
        
        # Get recipe names for context
        recipe_names = [recipe["name"] for recipe in RECIPES["recipes"].values()]
        
        super().__init__(
            instructions=f"""You are a friendly food and grocery ordering assistant for FreshMart, a fictional grocery store.

Your personality:
- Warm, helpful, and conversational
- You speak naturally and concisely since this is a voice interaction
- You confirm actions clearly so users know what happened
- You ask for clarification when needed (quantity, size, brand preferences)

Your capabilities:
- Help users browse and order from our catalog
- Add items to cart with specific quantities
- Remove items or update quantities
- Show what's in the cart
- Handle "ingredients for X" requests (like "I need ingredients for a peanut butter sandwich")
- Process orders when users are done

Available items in our catalog include: {', '.join(catalog_items[:10])}... and more.

We can also help with ingredient bundles for: {', '.join(recipe_names)}.

When users say things like:
- "I need ingredients for pasta" - use the add_recipe_ingredients tool
- "Add 2 breads to my cart" - use the add_to_cart tool
- "What's in my cart?" - use the show_cart tool
- "Remove the milk" - use the remove_from_cart tool
- "I'm done" or "Place my order" - use the place_order tool
- "What do you have?" - use the show_catalog tool

Always confirm what you've added or changed in the cart.
Keep responses brief and conversational for voice.
If an item isn't found, suggest similar alternatives from the catalog."""
        )
    
    @function_tool
    async def add_to_cart(
        self, 
        context: RunContext, 
        item_name: str, 
        quantity: int = 1,
        notes: str = ""
    ) -> str:
        """Add an item to the shopping cart.
        
        Args:
            item_name: The name of the item to add (e.g., "bread", "milk", "cheese pizza")
            quantity: How many to add (default 1)
            notes: Any special notes like "whole wheat" or "large size"
        """
        logger.info(f"Adding to cart: {item_name} x{quantity}")
        
        item = find_item_in_catalog(item_name)
        if not item:
            return f"Sorry, I couldn't find '{item_name}' in our catalog. Try asking what items we have available."
        
        result = self.cart.add_item(
            item_id=item["id"],
            name=item["name"],
            price=item["price"],
            quantity=quantity,
            notes=notes
        )
        
        return f"{result}. Your cart total is now ${self.cart.get_total():.2f}."
    
    @function_tool
    async def remove_from_cart(self, context: RunContext, item_name: str) -> str:
        """Remove an item from the shopping cart.
        
        Args:
            item_name: The name of the item to remove
        """
        logger.info(f"Removing from cart: {item_name}")
        
        # Find the item in cart by name
        search_lower = item_name.lower()
        for item_id, cart_item in self.cart.items.items():
            if search_lower in cart_item.name.lower():
                result = self.cart.remove_item(item_id)
                return f"{result}. Your cart total is now ${self.cart.get_total():.2f}."
        
        return f"I don't see '{item_name}' in your cart."
    
    @function_tool
    async def update_cart_quantity(
        self, 
        context: RunContext, 
        item_name: str, 
        quantity: int
    ) -> str:
        """Update the quantity of an item in the cart.
        
        Args:
            item_name: The name of the item to update
            quantity: The new quantity (use 0 to remove)
        """
        logger.info(f"Updating quantity: {item_name} to {quantity}")
        
        # Find the item in cart by name
        search_lower = item_name.lower()
        for item_id, cart_item in self.cart.items.items():
            if search_lower in cart_item.name.lower():
                result = self.cart.update_quantity(item_id, quantity)
                return f"{result}. Your cart total is now ${self.cart.get_total():.2f}."
        
        return f"I don't see '{item_name}' in your cart."
    
    @function_tool
    async def show_cart(self, context: RunContext) -> str:
        """Show the current contents of the shopping cart."""
        logger.info("Showing cart contents")
        return self.cart.get_cart_summary()
    
    @function_tool
    async def show_catalog(self, context: RunContext, category: str = "") -> str:
        """Show available items in the catalog.
        
        Args:
            category: Optional category to filter by (groceries, snacks, prepared_food, beverages)
        """
        logger.info(f"Showing catalog, category: {category}")
        
        if category:
            category_lower = category.lower().replace(" ", "_")
            if category_lower in CATALOG["catalog"]:
                items = CATALOG["catalog"][category_lower]
                lines = [f"Here's what we have in {category}:"]
                for item in items:
                    lines.append(f"- {item['name']}: ${item['price']:.2f}")
                return "\n".join(lines)
            else:
                return f"Category '{category}' not found. We have: groceries, snacks, prepared food, and beverages."
        
        return get_catalog_summary()
    
    @function_tool
    async def add_recipe_ingredients(
        self, 
        context: RunContext, 
        recipe_name: str,
        servings: int = 1
    ) -> str:
        """Add all ingredients for a recipe or meal to the cart.
        
        Use this when the user wants ingredients for a specific dish like:
        - "ingredients for a peanut butter sandwich"
        - "what I need for pasta"
        - "stuff for breakfast"
        
        Args:
            recipe_name: The name of the dish or recipe (e.g., "peanut butter sandwich", "spaghetti", "breakfast")
            servings: Number of servings/portions (multiplies quantities)
        """
        logger.info(f"Adding recipe ingredients for: {recipe_name}, servings: {servings}")
        
        recipe = find_recipe(recipe_name)
        if not recipe:
            return f"I don't have a recipe for '{recipe_name}'. I can help with: peanut butter sandwich, PB&J, spaghetti, grilled cheese, breakfast, salad, bruschetta, movie night snacks, or healthy snack pack."
        
        added_items = []
        for ingredient in recipe["ingredients"]:
            item_id = ingredient["item_id"]
            quantity = ingredient["quantity"] * servings
            
            # Find item details in catalog
            for category, items in CATALOG["catalog"].items():
                for item in items:
                    if item["id"] == item_id:
                        note = ingredient.get("note", "")
                        self.cart.add_item(
                            item_id=item["id"],
                            name=item["name"],
                            price=item["price"],
                            quantity=quantity,
                            notes=note
                        )
                        added_items.append(item["name"])
                        break
        
        if added_items:
            items_str = ", ".join(added_items)
            return f"I've added the ingredients for {recipe['name']} to your cart: {items_str}. Your cart total is now ${self.cart.get_total():.2f}."
        
        return "Sorry, I had trouble adding those ingredients."
    
    @function_tool
    async def set_customer_info(
        self, 
        context: RunContext, 
        name: str = "",
        address: str = ""
    ) -> str:
        """Set customer information for the order.
        
        Args:
            name: Customer's name
            address: Delivery address
        """
        if name:
            self.cart.customer_name = name
        if address:
            self.cart.customer_address = address
        
        response_parts = []
        if name:
            response_parts.append(f"name as {name}")
        if address:
            response_parts.append(f"address as {address}")
        
        if response_parts:
            return f"Got it! I've saved your {' and '.join(response_parts)}."
        return "Please provide your name or address."
    
    @function_tool
    async def place_order(
        self, 
        context: RunContext,
        customer_name: str = ""
    ) -> str:
        """Place the final order and save it to a JSON file.
        
        Call this when the user indicates they're done ordering, such as:
        - "That's all"
        - "I'm done"
        - "Place my order"
        - "Checkout"
        
        Args:
            customer_name: Optional customer name for the order
        """
        logger.info("Placing order")
        
        if not self.cart.items:
            return "Your cart is empty! Add some items before placing an order."
        
        if customer_name:
            self.cart.customer_name = customer_name
        
        # Create order object
        order = {
            "order_id": f"ORD-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "timestamp": datetime.now().isoformat(),
            "customer_name": self.cart.customer_name or "Guest",
            "customer_address": self.cart.customer_address,
            "items": [item.to_dict() for item in self.cart.items.values()],
            "total": self.cart.get_total(),
            "status": "placed"
        }
        
        # Save to JSON file
        orders_dir = SCRIPT_DIR / "orders"
        orders_dir.mkdir(exist_ok=True)
        
        order_file = orders_dir / f"{order['order_id']}.json"
        with open(order_file, "w") as f:
            json.dump(order, f, indent=2)
        
        logger.info(f"Order saved to {order_file}")
        
        # Generate order summary
        items_summary = ", ".join([
            f"{item.quantity}x {item.name}" 
            for item in self.cart.items.values()
        ])
        
        # Clear cart after order
        total = self.cart.get_total()
        customer = self.cart.customer_name or "valued customer"
        self.cart.clear()
        
        return f"Order placed successfully! Order ID: {order['order_id']}. Thank you {customer}! Your order includes: {items_summary}. Total: ${total:.2f}. Your order has been saved and will be ready soon!"


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


async def entrypoint(ctx: JobContext):
    # Logging setup
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    # Set up voice AI pipeline
    session = AgentSession(
        # Speech-to-text
        stt=deepgram.STT(model="nova-3"),
        # Large Language Model
        llm=google.LLM(model="gemini-2.5-flash"),
        # Text-to-speech
        tts=murf.TTS(
            voice="en-US-matthew", 
            style="Conversation",
            tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
            text_pacing=True
        ),
        # Turn detection and VAD
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=True,
    )

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

    # Start the session with the Food Ordering Assistant
    await session.start(
        agent=FoodOrderingAssistant(),
        room=ctx.room,
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )

    # Join the room and connect to the user
    await ctx.connect()
    
    # Send initial greeting
    await session.say(
        "Hi there! Welcome to FreshMart. I'm your food and grocery ordering assistant. "
        "I can help you order groceries, snacks, prepared meals, and even put together "
        "ingredients for recipes. What can I get for you today?"
    )


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))
