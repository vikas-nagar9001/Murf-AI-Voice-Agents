# Fraud Alert Voice Agent - Implementation Guide

## Overview
This is a fraud detection voice agent for SecureBank that handles suspicious transaction alerts. The agent follows a structured conversation flow to verify customer identity and determine if transactions are legitimate.

## Features Implemented

### ✅ Primary Goal (MVP) - Completed
1. **Fraud Cases Database**: SQLite database with sample fraud cases including:
   - Customer information (name, security identifier)
   - Transaction details (amount, merchant, location, time)
   - Security verification questions
   - Case status tracking

2. **Fraud Agent Persona**: Professional bank fraud department representative that:
   - Introduces itself as SecureBank's fraud department
   - Uses calm, professional, and reassuring language
   - Never asks for sensitive information like full card numbers or PINs

3. **Conversation Flow**:
   - Greets customer and explains the call purpose
   - Loads fraud case by customer name
   - Performs identity verification using security questions
   - Reads suspicious transaction details
   - Asks if customer made the transaction
   - Updates case status based on response

4. **Database Persistence**: All case outcomes are saved back to the database

## Sample Database Entries
The system includes three sample fraud cases:

1. **John** - ABC Industry transaction ($299.99)
2. **Sarah** - Luxury Goods Store transaction ($1,299.99) 
3. **Mike** - Gaming Platform transaction ($99.99)

## How to Test the Agent

### 1. Start the Application
```bash
# Terminal 1 - Backend
cd backend
uv run python src/agent.py dev

# Terminal 2 - Frontend
cd frontend
pnpm dev
```

### 2. Connect to the Agent
1. Open http://localhost:3000
2. Click "Connect to Fraud Department"
3. Allow microphone permissions

### 3. Test the Fraud Flow
Follow this conversation flow:

**Agent**: "Hello, this is SecureBank's fraud department..."

**You**: "Hi, this is John" (or "Sarah" or "Mike")

**Agent**: "Found a fraud alert for John. I can see a suspicious transaction on your account. For security purposes, I need to verify your identity. What is your mother's maiden name?"

**You**: "Smith" (for John) / "Fluffy" (for Sarah) / "Chicago" (for Mike)

**Agent**: "Thank you for verifying your identity. Here are the details of the suspicious transaction: [reads transaction details]"

**You**: "Yes, I made that transaction" or "No, I didn't make that transaction"

**Agent**: [Updates case and provides appropriate response]

## Technical Implementation

### Database Schema
```sql
CREATE TABLE fraud_cases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_name TEXT NOT NULL,
    security_identifier TEXT NOT NULL,
    card_ending TEXT NOT NULL,
    case_status TEXT DEFAULT 'pending_review',
    transaction_name TEXT NOT NULL,
    transaction_time TEXT NOT NULL,
    transaction_category TEXT NOT NULL,
    transaction_source TEXT NOT NULL,
    transaction_amount REAL NOT NULL,
    transaction_location TEXT NOT NULL,
    security_question TEXT NOT NULL,
    security_answer TEXT NOT NULL,
    outcome_note TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
)
```

### Agent Tools
1. `load_fraud_case(username)` - Loads pending fraud case for customer
2. `get_security_question()` - Gets security question for verification
3. `verify_customer(security_answer)` - Verifies customer identity
4. `get_transaction_details()` - Provides transaction details after verification
5. `confirm_transaction(user_made_transaction)` - Records customer decision and updates case

### Case Status Flow
- `pending_review` → `confirmed_safe` (if customer confirms transaction)
- `pending_review` → `confirmed_fraud` (if customer denies transaction)

## Security Features
- Only asks non-sensitive security questions
- Never requests full card numbers, PINs, or passwords
- Requires identity verification before sharing transaction details
- All data is fake/demo data only

## Files Modified/Created
- `backend/src/fraud_database.py` - Database management
- `backend/src/agent.py` - Main agent implementation
- `frontend/app-config.ts` - Updated branding for fraud system
- `fraud_cases.db` - SQLite database (auto-created)

## Future Enhancements (Advanced Goals)
- LiveKit Telephony integration for real phone calls
- Multiple fraud cases per customer
- DTMF input support
- Enhanced logging and audit trails
- Real-time fraud detection algorithms

## Testing Notes
The agent successfully:
- ✅ Loads fraud cases by username
- ✅ Verifies customer identity
- ✅ Reads transaction details clearly
- ✅ Processes customer decisions
- ✅ Updates database with outcomes
- ✅ Maintains professional fraud department persona
- ✅ Uses proper conversation flow

This implementation provides a complete MVP fraud alert voice agent that can be extended with telephony and additional features as needed.