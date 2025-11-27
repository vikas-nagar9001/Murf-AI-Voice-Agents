#!/usr/bin/env python3

from src.fraud_database import FraudDatabase

def test_database():
    try:
        db = FraudDatabase()
        print("Database initialized successfully")
        
        cases = db.get_all_cases()
        print(f"Found {len(cases)} fraud cases:")
        
        for case in cases:
            print(f"- {case['user_name']}: {case['transaction_name']} for ${case['transaction_amount']}")
            
        # Test loading a specific case
        john_case = db.get_fraud_case_by_username("John")
        if john_case:
            print(f"\nLoaded case for John: {john_case['transaction_name']}")
        else:
            print("\nNo case found for John")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_database()