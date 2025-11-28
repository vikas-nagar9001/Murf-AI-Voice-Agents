# FreshMart Voice Agent - Demo Conversation

This document shows example conversations demonstrating the food ordering voice agent's capabilities.

---

## Demo 1: Basic Item Ordering

**Agent:** Hi there! Welcome to FreshMart. I'm your food and grocery ordering assistant. I can help you order groceries, snacks, prepared meals, and even put together ingredients for recipes. What can I get for you today?

**User:** I'd like some milk please.

**Agent:** Added 1 Whole Milk to your cart. Your cart total is now $3.79.

**User:** Can you add 2 loaves of wheat bread?

**Agent:** Added 2 Whole Wheat Bread to your cart. Your cart total is now $10.77.

**User:** Actually, make that 3 loaves of bread.

**Agent:** Updated Whole Wheat Bread quantity to 3. Your cart total is now $14.26.

**User:** What's in my cart?

**Agent:** Here's what's in your cart:
- 1x Whole Milk: $3.79
- 3x Whole Wheat Bread: $10.47

Total: $14.26

---

## Demo 2: Recipe-Based Ordering (Intelligent Bundling)

**Agent:** Hi there! Welcome to FreshMart. I'm your food and grocery ordering assistant. What can I get for you today?

**User:** I need ingredients for a peanut butter sandwich.

**Agent:** I've added the ingredients for Peanut Butter Sandwich to your cart: White Bread, Creamy Peanut Butter. Your cart total is now $7.28.

**User:** Actually, can I get ingredients for a PB&J instead?

**Agent:** I've added the ingredients for PB&J Sandwich to your cart: White Bread, Creamy Peanut Butter, Grape Jelly. Your cart total is now $17.85.

**User:** What do I need for spaghetti dinner for 2 people?

**Agent:** I've added the ingredients for Spaghetti with Marinara to your cart: Spaghetti Pasta, Marinara Sauce, Extra Virgin Olive Oil, Fresh Garlic. Your cart total is now $32.81.

---

## Demo 3: Browsing the Catalog

**User:** What snacks do you have?

**Agent:** Here's what we have in snacks:
- Classic Potato Chips: $3.99
- Chocolate Chip Cookies: $4.49
- Honey Oat Granola Bars: $4.99
- Classic Trail Mix: $5.49
- Butter Popcorn: $3.49

**User:** I'll take the trail mix and some popcorn.

**Agent:** Added 1 Classic Trail Mix to your cart. Your cart total is now $5.49.
Added 1 Butter Popcorn to your cart. Your cart total is now $8.98.

---

## Demo 4: Movie Night Bundle

**User:** I'm having a movie night. What do you recommend?

**Agent:** I can put together a perfect movie night bundle for you! Want me to add our movie night snacks package? It includes popcorn, chips, cola, and chocolate chip cookies.

**User:** Yes, that sounds great!

**Agent:** I've added the ingredients for Movie Night Snacks to your cart: Butter Popcorn, Classic Potato Chips, Classic Cola (2), Chocolate Chip Cookies. Your cart total is now $15.95.

---

## Demo 5: Removing Items & Checkout

**User:** What's in my cart?

**Agent:** Here's what's in your cart:
- 1x Butter Popcorn: $3.49
- 1x Classic Potato Chips: $3.99
- 2x Classic Cola: $3.98
- 1x Chocolate Chip Cookies: $4.49

Total: $15.95

**User:** Remove the chips please.

**Agent:** Removed Classic Potato Chips from your cart. Your cart total is now $11.96.

**User:** That's all, I'm done ordering.

**Agent:** Order placed successfully! Order ID: ORD-20251128143022. Thank you valued customer! Your order includes: 1x Butter Popcorn, 2x Classic Cola, 1x Chocolate Chip Cookies. Total: $11.96. Your order has been saved and will be ready soon!

---

## Demo 6: Complete Ordering Flow with Customer Info

**User:** Hi, I'd like to order some groceries.

**Agent:** Hi there! Welcome to FreshMart. What can I get for you today?

**User:** I need eggs, butter, and orange juice for breakfast.

**Agent:** Added 1 Farm Fresh Eggs to your cart. Your cart total is now $4.99.
Added 1 Unsalted Butter to your cart. Your cart total is now $9.48.
Added 1 Fresh Orange Juice to your cart. Your cart total is now $14.47.

**User:** Add a cheese pizza too.

**Agent:** Added 1 Cheese Pizza to your cart. Your cart total is now $27.46.

**User:** My name is John and I live at 123 Main Street.

**Agent:** Got it! I've saved your name as John and address as 123 Main Street.

**User:** Place my order please.

**Agent:** Order placed successfully! Order ID: ORD-20251128144512. Thank you John! Your order includes: 1x Farm Fresh Eggs, 1x Unsalted Butter, 1x Fresh Orange Juice, 1x Cheese Pizza. Total: $27.46. Your order has been saved and will be ready soon!

---

## Sample Order JSON Output

When an order is placed, it's saved to `backend/src/orders/ORD-YYYYMMDDHHMMSS.json`:

```json
{
  "order_id": "ORD-20251128144512",
  "timestamp": "2025-11-28T14:45:12.345678",
  "customer_name": "John",
  "customer_address": "123 Main Street",
  "items": [
    {
      "item_id": "eggs-dozen",
      "name": "Farm Fresh Eggs",
      "price": 4.99,
      "quantity": 1,
      "notes": "",
      "subtotal": 4.99
    },
    {
      "item_id": "butter",
      "name": "Unsalted Butter",
      "price": 4.49,
      "quantity": 1,
      "notes": "",
      "subtotal": 4.49
    },
    {
      "item_id": "juice-orange",
      "name": "Fresh Orange Juice",
      "price": 4.99,
      "quantity": 1,
      "notes": "",
      "subtotal": 4.99
    },
    {
      "item_id": "pizza-cheese",
      "name": "Cheese Pizza",
      "price": 12.99,
      "quantity": 1,
      "notes": "",
      "subtotal": 12.99
    }
  ],
  "total": 27.46,
  "status": "placed"
}
```

---

## Available Recipe Bundles

Users can ask for "ingredients for X" where X is:

| Request | Items Added |
|---------|-------------|
| Peanut butter sandwich | White Bread, Peanut Butter |
| PB&J / Peanut butter and jelly | White Bread, Peanut Butter, Grape Jelly |
| Spaghetti / Pasta dinner | Spaghetti, Marinara Sauce, Olive Oil, Garlic |
| Grilled cheese | White Bread, Cheddar Cheese, Butter |
| Breakfast | Eggs, White Bread, Butter, Orange Juice |
| Salad | Romaine Lettuce, Tomatoes, Olive Oil |
| Bruschetta | White Bread, Tomatoes, Garlic, Olive Oil |
| Movie night snacks | Popcorn, Chips, Cola (2), Cookies |
| Healthy snack pack | Granola Bars, Trail Mix, Water (2) |

---

## Tips for Testing

1. **Start the agent**: `cd backend && python -m src.agent dev`
2. **Start the frontend**: `cd frontend && pnpm dev`
3. **Open browser**: Navigate to `http://localhost:3000`
4. **Test basic ordering**: "Add milk to my cart"
5. **Test recipe bundles**: "I need ingredients for pasta"
6. **Test cart operations**: "What's in my cart?", "Remove the milk"
7. **Complete order**: "I'm done" or "Place my order"
8. **Check saved order**: Look in `backend/src/orders/` folder
