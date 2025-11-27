import sqlite3
import os
import json
from typing import Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger("fraud_database")

class FraudDatabase:
    """Manages fraud cases in SQLite database"""
    
    def __init__(self, db_path: str = "fraud_cases.db"):
        self.db_path = db_path
        self.init_database()
        
    def init_database(self):
        """Initialize database and create tables if they don't exist"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create fraud_cases table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS fraud_cases (
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
            """)
            
            # Check if we need to populate with sample data
            cursor.execute("SELECT COUNT(*) FROM fraud_cases")
            if cursor.fetchone()[0] == 0:
                self._populate_sample_data(cursor)
                
            conn.commit()
    
    def _populate_sample_data(self, cursor):
        """Populate database with sample fraud cases"""
        sample_cases = [
            {
                "user_name": "John",
                "security_identifier": "12345",
                "card_ending": "4242",
                "case_status": "pending_review",
                "transaction_name": "ABC Industry",
                "transaction_time": "2024-11-26 14:30:00",
                "transaction_category": "e-commerce",
                "transaction_source": "alibaba.com",
                "transaction_amount": 299.99,
                "transaction_location": "Shanghai, China",
                "security_question": "What is your mother's maiden name?",
                "security_answer": "Smith"
            },
            {
                "user_name": "Sarah",
                "security_identifier": "67890",
                "card_ending": "8765",
                "case_status": "pending_review", 
                "transaction_name": "Luxury Goods Store",
                "transaction_time": "2024-11-26 09:15:00",
                "transaction_category": "retail",
                "transaction_source": "luxurystore.com",
                "transaction_amount": 1299.99,
                "transaction_location": "Paris, France",
                "security_question": "What was your first pet's name?",
                "security_answer": "Fluffy"
            },
            {
                "user_name": "Mike",
                "security_identifier": "11111",
                "card_ending": "1234",
                "case_status": "pending_review",
                "transaction_name": "Gaming Platform",
                "transaction_time": "2024-11-25 23:45:00",
                "transaction_category": "gaming",
                "transaction_source": "gaming-platform.com",
                "transaction_amount": 99.99,
                "transaction_location": "Los Angeles, CA",
                "security_question": "What city were you born in?",
                "security_answer": "Chicago"
            }
        ]
        
        for case in sample_cases:
            cursor.execute("""
                INSERT INTO fraud_cases (
                    user_name, security_identifier, card_ending, case_status,
                    transaction_name, transaction_time, transaction_category,
                    transaction_source, transaction_amount, transaction_location,
                    security_question, security_answer
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                case["user_name"], case["security_identifier"], case["card_ending"],
                case["case_status"], case["transaction_name"], case["transaction_time"],
                case["transaction_category"], case["transaction_source"], case["transaction_amount"],
                case["transaction_location"], case["security_question"], case["security_answer"]
            ))
            
        logger.info("Populated database with sample fraud cases")
    
    def get_fraud_case_by_username(self, username: str) -> Optional[Dict]:
        """Get a pending fraud case by username"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM fraud_cases 
                WHERE user_name = ? AND case_status = 'pending_review'
                LIMIT 1
            """, (username,))
            
            row = cursor.fetchone()
            if not row:
                return None
                
            columns = [description[0] for description in cursor.description]
            return dict(zip(columns, row))
    
    def update_case_status(self, case_id: int, status: str, outcome_note: str = "") -> bool:
        """Update fraud case status and outcome"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE fraud_cases 
                    SET case_status = ?, outcome_note = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (status, outcome_note, case_id))
                
                conn.commit()
                logger.info(f"Updated case {case_id} to status: {status}")
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"Error updating case {case_id}: {e}")
            return False
    
    def get_all_cases(self) -> List[Dict]:
        """Get all fraud cases (for debugging/testing)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM fraud_cases")
            
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]