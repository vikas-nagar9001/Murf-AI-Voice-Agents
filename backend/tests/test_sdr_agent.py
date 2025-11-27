import pytest
import json
import os
import sys
from unittest.mock import Mock, patch

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from agent import Assistant, LeadData


class TestSDRAgent:
    """Test the SDR agent functionality"""
    
    def setup_method(self):
        """Set up test fixtures before each test method"""
        self.assistant = Assistant()
    
    def test_lead_data_initialization(self):
        """Test LeadData class initialization"""
        lead = LeadData()
        assert lead.name is None
        assert lead.company is None
        assert lead.email is None
        assert lead.role is None
        assert lead.use_case is None
        assert lead.team_size is None
        assert lead.timeline is None
    
    def test_lead_data_to_dict(self):
        """Test LeadData to_dict conversion"""
        lead = LeadData()
        lead.name = "John Doe"
        lead.company = "Test Corp"
        lead.email = "john@testcorp.com"
        
        lead_dict = lead.to_dict()
        assert lead_dict['name'] == "John Doe"
        assert lead_dict['company'] == "Test Corp"
        assert lead_dict['email'] == "john@testcorp.com"
        assert 'collected_at' in lead_dict
    
    def test_lead_data_collected_fields(self):
        """Test getting collected fields from LeadData"""
        lead = LeadData()
        assert lead.get_collected_fields() == []
        
        lead.name = "Jane"
        lead.email = "jane@example.com"
        collected = lead.get_collected_fields()
        assert "name" in collected
        assert "email" in collected
        assert len(collected) == 2
    
    def test_company_data_loading(self):
        """Test that company data is loaded correctly"""
        # Check if company data is loaded
        assert self.assistant.company_data is not None
        assert 'company' in self.assistant.company_data
        assert 'faq' in self.assistant.company_data
        assert self.assistant.company_data['company']['name'] == 'Razorpay'
    
    def test_faq_search_basic(self):
        """Test basic FAQ search functionality"""
        # Test "what does" question
        result = self.assistant._search_faq("what does razorpay do")
        assert result is not None
        assert "payments platform" in result.lower()
        
        # Test pricing question
        result = self.assistant._search_faq("how much does it cost")
        assert result is not None
        assert "2%" in result or "transaction" in result.lower()
        
        # Test free tier question
        result = self.assistant._search_faq("do you have free tier")
        assert result is not None
        assert "free tier" in result.lower() or "pay" in result.lower()
    
    def test_faq_search_keywords(self):
        """Test FAQ search with various keywords"""
        # Test payment methods
        result = self.assistant._search_faq("what payment methods")
        assert result is not None
        assert "upi" in result.lower() or "payment method" in result.lower()
        
        # Test security
        result = self.assistant._search_faq("is it secure")
        assert result is not None
        assert "secure" in result.lower() or "pci" in result.lower()
        
        # Test integration
        result = self.assistant._search_faq("how to integrate")
        assert result is not None
        assert "integration" in result.lower() or "api" in result.lower()
    
    def test_faq_search_no_match(self):
        """Test FAQ search when no match is found"""
        result = self.assistant._search_faq("completely unrelated query")
        assert result is None
    
    @patch('builtins.open', create=True)
    @patch('os.makedirs')
    @patch('os.path.exists')
    @patch('json.dump')
    def test_save_lead_data(self, mock_json_dump, mock_exists, mock_makedirs, mock_open):
        """Test saving lead data to file"""
        # Setup mocks
        mock_exists.return_value = False
        mock_file = Mock()
        mock_open.return_value.__enter__.return_value = mock_file
        
        # Set up some lead data
        self.assistant.lead.name = "Test User"
        self.assistant.lead.company = "Test Company"
        self.assistant.lead.email = "test@example.com"
        
        # Call save method
        filename = self.assistant._save_lead_data()
        
        # Verify directory creation
        mock_makedirs.assert_called_once_with("leads")
        
        # Verify file operations
        mock_open.assert_called_once()
        mock_json_dump.assert_called_once()
        
        # Verify filename format
        assert filename is not None
        assert filename.startswith("leads/lead_")
        assert filename.endswith(".json")
    
    def test_assistant_initialization(self):
        """Test Assistant class initialization"""
        assert self.assistant.lead is not None
        assert self.assistant.conversation_stage == "greeting"
        assert self.assistant.company_data is not None


class TestSDRWorkflow:
    """Integration tests for the complete SDR workflow"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.assistant = Assistant()
    
    def test_greeting_to_qualification_flow(self):
        """Test the flow from greeting to lead qualification"""
        # Initial state should be greeting
        assert self.assistant.conversation_stage == "greeting"
        
        # No lead data initially
        assert len(self.assistant.lead.get_collected_fields()) == 0
    
    def test_lead_collection_workflow(self):
        """Test the complete lead collection workflow"""
        # Simulate collecting different pieces of lead information
        lead_data = {
            "name": "Rahul Kumar",
            "company": "TechStart India",
            "email": "rahul@techstart.co.in",
            "role": "CTO",
            "use_case": "integrate payment gateway for e-commerce platform",
            "team_size": "15 people",
            "timeline": "next month"
        }
        
        # Set lead data
        for field, value in lead_data.items():
            if field == "name":
                self.assistant.lead.name = value
            elif field == "company":
                self.assistant.lead.company = value
            elif field == "email":
                self.assistant.lead.email = value
            elif field == "role":
                self.assistant.lead.role = value
            elif field == "use_case":
                self.assistant.lead.use_case = value
            elif field == "team_size":
                self.assistant.lead.team_size = value
            elif field == "timeline":
                self.assistant.lead.timeline = value
        
        # Verify all fields are collected
        collected_fields = self.assistant.lead.get_collected_fields()
        assert len(collected_fields) == 7
        assert "name" in collected_fields
        assert "company" in collected_fields
        assert "email" in collected_fields
        assert "role" in collected_fields
        assert "use case" in collected_fields
        assert "team size" in collected_fields
        assert "timeline" in collected_fields


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])