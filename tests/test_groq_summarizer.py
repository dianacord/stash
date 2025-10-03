import pytest
from unittest.mock import Mock, patch
from backend.services.groq_summarizer import GroqSummarizer
import os

def test_groq_summarizer_initialization():
    """Test GroqSummarizer initializes with API key"""
    os.environ['GROQ_API_KEY'] = 'test_key'
    summarizer = GroqSummarizer()
    assert summarizer.client is not None

def test_groq_summarizer_no_api_key():
    """Test GroqSummarizer raises error without API key"""
    if 'GROQ_API_KEY' in os.environ:
        del os.environ['GROQ_API_KEY']
    
    with pytest.raises(ValueError):
        GroqSummarizer()

@patch('backend.services.groq_summarizer.Groq')
def test_summarize_success(mock_groq):
    """Test successful summarization"""
    os.environ['GROQ_API_KEY'] = 'test_key'
    
    # Mock the Groq API response
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = "Test summary"
    
    mock_client = Mock()
    mock_client.chat.completions.create.return_value = mock_response
    mock_groq.return_value = mock_client
    
    summarizer = GroqSummarizer()
    result = summarizer.summarize("Test transcript")
    
    assert result['success'] == True
    assert result['summary'] == "Test summary"

@patch('backend.services.groq_summarizer.Groq')
def test_summarize_truncates_long_transcript(mock_groq):
    """Test summarizer truncates long transcripts"""
    os.environ['GROQ_API_KEY'] = 'test_key'
    
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = "Summary"
    
    mock_client = Mock()
    mock_client.chat.completions.create.return_value = mock_response
    mock_groq.return_value = mock_client
    
    summarizer = GroqSummarizer()
    long_transcript = "x" * 10000
    result = summarizer.summarize(long_transcript, max_length=4000)
    
    # Check that the result is successful
    assert result['success'] == True
    assert result['summary'] == "Summary"
    
    # Check that the API was called with truncated transcript
    call_args = mock_client.chat.completions.create.call_args
    assert len(call_args[1]['messages'][1]['content']) < 10000

@patch('backend.services.groq_summarizer.Groq')
def test_summarize_api_error(mock_groq):
    """Test summarizer handles API errors"""
    os.environ['GROQ_API_KEY'] = 'test_key'
    
    mock_client = Mock()
    mock_client.chat.completions.create.side_effect = Exception("API Error")
    mock_groq.return_value = mock_client
    
    summarizer = GroqSummarizer()
    result = summarizer.summarize("Test transcript")
    
    assert result['success'] == False
    assert 'error' in result