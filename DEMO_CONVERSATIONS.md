# Fraud Alert Voice Agent - Demo Conversation Scripts

## Demo Conversation 1: Legitimate Transaction (John)

**Agent**: Hello, this is SecureBank's fraud department. We're calling about a potentially suspicious transaction on your account. May I please have your name to look up your case?

**Customer**: Hi, this is John.

**Agent**: Thank you John. I found a fraud alert for you. I can see a suspicious transaction on your account. For security purposes, I need to verify your identity. What is your mother's maiden name?

**Customer**: Smith.

**Agent**: Thank you for verifying your identity. Now let me tell you about the suspicious transaction. Here are the details of the suspicious transaction: A transaction of $299.99 at ABC Industry from alibaba.com in Shanghai, China on 2024-11-26 14:30:00 using your card ending in 4242. Did you make this transaction?

**Customer**: Yes, I made that purchase. I ordered some equipment for my business.

**Agent**: Perfect! I've updated your account to show this transaction is legitimate. No further action is needed. Thank you for your time and have a great day.

---

## Demo Conversation 2: Fraudulent Transaction (Sarah)

**Agent**: Hello, this is SecureBank's fraud department. We're calling about a potentially suspicious transaction on your account. May I please have your name to look up your case?

**Customer**: This is Sarah.

**Agent**: Thank you Sarah. I found a fraud alert for you. I can see a suspicious transaction on your account. For security purposes, I need to verify your identity. What was your first pet's name?

**Customer**: Fluffy.

**Agent**: Thank you for verifying your identity. Now let me tell you about the suspicious transaction. Here are the details of the suspicious transaction: A transaction of $1299.99 at Luxury Goods Store from luxurystore.com in Paris, France on 2024-11-26 09:15:00 using your card ending in 8765. Did you make this transaction?

**Customer**: No, I definitely did not make that purchase. I've never been to Paris and I don't shop at luxury stores.

**Agent**: I understand this transaction is fraudulent. I've immediately blocked your card ending in 8765 and initiated a dispute. You'll receive a new card within 3-5 business days. Is there anything else I can help you with regarding this matter?

**Customer**: No, that covers everything. Thank you for catching this so quickly.

**Agent**: You're welcome. Your account is now secure. Have a great day.

---

## Demo Conversation 3: Failed Verification (Mike)

**Agent**: Hello, this is SecureBank's fraud department. We're calling about a potentially suspicious transaction on your account. May I please have your name to look up your case?

**Customer**: This is Mike.

**Agent**: Thank you Mike. I found a fraud alert for you. I can see a suspicious transaction on your account. For security purposes, I need to verify your identity. What city were you born in?

**Customer**: New York.

**Agent**: I'm sorry, but that answer doesn't match our records. For your security, I cannot proceed with this call. Please visit your nearest SecureBank branch with proper identification to address this fraud alert. Thank you.

---

## Demo Conversation 4: Customer Not Found

**Agent**: Hello, this is SecureBank's fraud department. We're calling about a potentially suspicious transaction on your account. May I please have your name to look up your case?

**Customer**: This is Robert.

**Agent**: Thank you Robert. I don't see any pending fraud alerts for Robert. You may have the wrong department. If you have concerns about your account, please call our main customer service line. Thank you.

---

## Demo Conversation 5: Complete Gaming Transaction (Mike - Success)

**Agent**: Hello, this is SecureBank's fraud department. We're calling about a potentially suspicious transaction on your account. May I please have your name to look up your case?

**Customer**: Hi, this is Mike.

**Agent**: Thank you Mike. I found a fraud alert for you. I can see a suspicious transaction on your account. For security purposes, I need to verify your identity. What city were you born in?

**Customer**: Chicago.

**Agent**: Thank you for verifying your identity. Now let me tell you about the suspicious transaction. Here are the details of the suspicious transaction: A transaction of $99.99 at Gaming Platform from gaming-platform.com in Los Angeles, CA on 2024-11-25 23:45:00 using your card ending in 1234. Did you make this transaction?

**Customer**: Yes, I bought a new game last night. I remember that purchase.

**Agent**: Perfect! I've updated your account to show this transaction is legitimate. No further action is needed. Thank you for your time.

---

## Key Testing Points

### Security Questions by Customer:
- **John**: "What is your mother's maiden name?" → Answer: "Smith"
- **Sarah**: "What was your first pet's name?" → Answer: "Fluffy"  
- **Mike**: "What city were you born in?" → Answer: "Chicago"

### Transaction Details:
- **John**: $299.99 at ABC Industry (Shanghai, China)
- **Sarah**: $1,299.99 at Luxury Goods Store (Paris, France)
- **Mike**: $99.99 at Gaming Platform (Los Angeles, CA)

### Expected Outcomes:
1. **Legitimate**: Case status → `confirmed_safe`
2. **Fraudulent**: Case status → `confirmed_fraud`, card blocked
3. **Wrong Answer**: Verification fails, call ends
4. **Name Not Found**: No fraud case exists

### Conversation Flow Validation:
✅ Professional introduction  
✅ Customer name collection  
✅ Case lookup  
✅ Identity verification  
✅ Transaction details provided  
✅ Customer decision recorded  
✅ Appropriate action taken  
✅ Database updated  
✅ Professional closure  

Use these scripts to test all possible conversation paths and validate the fraud agent's behavior.