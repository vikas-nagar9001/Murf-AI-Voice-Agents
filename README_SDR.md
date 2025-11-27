# Razorpay SDR Voice Agent

This is a voice-enabled Sales Development Representative (SDR) agent built for Razorpay using LiveKit Agents. The agent can conduct natural conversations with prospects, answer product questions, and collect lead information.

## Features

### 🎯 SDR Capabilities
- **Natural Greeting**: Warmly greets visitors and asks about their needs
- **Product Knowledge**: Answers questions about Razorpay's products and services using FAQ data
- **Lead Qualification**: Naturally collects prospect information during conversations
- **Call Summary**: Provides verbal summaries and saves lead data to JSON files

### 🏢 Company Focus: Razorpay
- **Products**: Payment Gateway, Payment Links, RazorpayX Business Banking, POS Solutions
- **Target Market**: Indian businesses, startups, e-commerce, SaaS platforms
- **Pricing**: Transparent 2% domestic transactions, 3% international
- **USP**: 100+ payment methods, instant settlements, business banking integration

### 💬 Conversation Flow
1. **Greeting Stage**: Introduces as Priya from Razorpay, asks what brought them
2. **Discovery**: Understands business needs and payment challenges  
3. **Product Q&A**: Answers questions using comprehensive FAQ database
4. **Lead Collection**: Naturally gathers contact and business information
5. **Summary**: Provides recap and saves lead data for follow-up

## Lead Data Collected

The agent collects the following information:
- **Name**: Contact person's name
- **Company**: Business/organization name  
- **Email**: Contact email address
- **Role**: Job title/position
- **Use Case**: What they want to use Razorpay for
- **Team Size**: Number of people in their organization
- **Timeline**: When they plan to implement (now/soon/later)

## File Structure

```
backend/src/
├── agent.py              # Main SDR agent implementation
├── company_data.json     # Razorpay company info, products, FAQ
└── leads/               # Directory for saved lead data (created automatically)
```

## Key Components

### 1. LeadData Class
Manages prospect information collection and storage:
- Tracks all lead fields
- Converts to JSON format
- Provides utility methods for field tracking

### 2. Assistant Class (SDR Agent)
- **Persona**: Friendly, professional Razorpay SDR named Priya
- **FAQ Search**: Keyword-based search through company knowledge base
- **Lead Tools**: Function tools for collecting and storing prospect data
- **Indian Voice**: Uses en-IN-priya voice for authenticity

### 3. Function Tools

#### `answer_product_question(question)`
- Searches FAQ database for relevant answers
- Handles questions about products, pricing, features, integrations
- Falls back gracefully for unknown topics

#### `collect_lead_info(field, value)`
- Stores prospect information as collected during conversation
- Maps various field descriptions to lead data structure
- Provides confirmation of collected information

#### `generate_call_summary()`
- Creates verbal summary of conversation
- Saves complete lead data to timestamped JSON file
- Handles both complete and partial lead scenarios

## FAQ Knowledge Base

Comprehensive coverage of common prospect questions:
- What does Razorpay do?
- Pricing and fees
- Payment methods supported
- Security and compliance  
- Integration options
- Business banking services
- International payments
- Support and onboarding

## Voice Pipeline Configuration

- **STT**: Deepgram Nova-3 for accurate speech recognition
- **LLM**: Google Gemini 2.5-Flash for intelligent responses  
- **TTS**: Murf en-IN-priya voice with conversation style
- **VAD**: Multilingual turn detection for smooth conversations

## Usage

1. **Start the Agent**:
   ```bash
   cd backend
   uv run python src/agent.py
   ```

2. **Connect**: Use LiveKit client to connect to the agent

3. **Conversation Example**:
   ```
   Agent: "Hi! I'm Priya from Razorpay. What brought you here today?"
   
   User: "I'm looking for a payment solution for my e-commerce site"
   
   Agent: "That's great! We help many e-commerce businesses accept payments. 
          What's your name and which company are you with?"
   
   User: "I'm Rahul from TechMart"
   
   Agent: "Nice to meet you Rahul! Tell me more about TechMart - what are you 
          selling and what payment challenges are you facing?"
   ```

4. **Lead Data**: Check `leads/` directory for saved prospect information

## Testing

Run comprehensive tests:
```bash
cd backend
uv run pytest tests/test_sdr_agent.py -v
```

Tests cover:
- Lead data management
- Company data loading  
- FAQ search functionality
- Lead collection workflow
- File saving operations

## Lead Storage

Each conversation generates a timestamped JSON file:
```json
{
  "name": "Rahul Kumar",
  "company": "TechMart",
  "email": "rahul@techmart.com",
  "role": "CTO", 
  "use_case": "integrate payment gateway for e-commerce",
  "team_size": "15 people",
  "timeline": "next month",
  "collected_at": "2025-11-27T20:45:30.123456"
}
```

## Customization

To adapt for different companies:

1. **Update Company Data**: Modify `company_data.json` with new company info
2. **Adjust Persona**: Update agent instructions in `Assistant.__init__()`
3. **Modify FAQ Search**: Enhance `_search_faq()` method for better matching
4. **Lead Fields**: Customize fields in `LeadData` class as needed

## MVP Completion Checklist

✅ **SDR Persona**: Agent acts as professional Razorpay SDR  
✅ **Product Q&A**: Answers company/product/pricing questions from FAQ  
✅ **Lead Collection**: Naturally collects and stores prospect information  
✅ **Call Summary**: Provides verbal recap and saves data to JSON  
✅ **Indian Company**: Focused on Razorpay with authentic Indian context  

The SDR agent successfully meets all MVP requirements and is ready for live conversations!