"""
Azure AI client for Claude API integration
"""
import logging
import requests
import os
from typing import Optional

logger = logging.getLogger(__name__)

# Azure configuration
AZURE_API_URL = os.getenv("AZURE_API_URL", "https://transformellica-gpt5-1.services.ai.azure.com/anthropic/v1/messages")
AZURE_API_KEY = os.getenv("AZURE_API_KEY", "")

# Initialize client
try:
    if not AZURE_API_KEY:
        logger.warning("⚠️ AZURE_API_KEY environment variable is not set!")
        logger.warning("   Please set it using:")
        logger.warning("   Windows: set AZURE_API_KEY=your_api_key")
        logger.warning("   Linux/Mac: export AZURE_API_KEY=your_api_key")
        raise ValueError("AZURE_API_KEY environment variable is required")
    
    logger.info(f"✅ Azure AI client initialized successfully")
    logger.info(f"   API URL: {AZURE_API_URL}")
except Exception as e:
    logger.error(f"❌ Failed to initialize Azure AI client: {str(e)}")
    raise


def call_claude_api(
    system_message: str,
    user_message: str,
    model: Optional[str] = None,
    max_tokens: int = 16384,
    temperature: float = 0.7,
    use_cache: bool = True
) -> Optional[str]:
    """
    Call Claude API via Azure OpenAI/Azure AI Foundry
    
    Args:
        system_message: System prompt for Claude
        user_message: User message/prompt
        model: Model ID (optional, defaults to whatever is configured in Azure)
        max_tokens: Maximum tokens in response
        temperature: Sampling temperature
        use_cache: Whether to use caching (placeholder for future implementation)
    
    Returns:
        str: Claude's response or None if failed
    """
    try:
        # Prepare headers
        headers = {
            "Content-Type": "application/json",
            "x-api-key": AZURE_API_KEY,
            "anthropic-version": "2023-06-01"
        }
        
        # Prepare the request body
        # If no model specified, don't include it - let Azure use its default deployment
        request_body = {
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system_message,
            "messages": [
                {
                    "role": "user",
                    "content": user_message
                }
            ]
        }
        
        # Only include model if explicitly provided
        if model:
            request_body["model"] = model
        
        logger.info(f"🔄 Calling Azure Claude API...")
        logger.debug(f"Request URL: {AZURE_API_URL}")
        logger.debug(f"Request body keys: {list(request_body.keys())}")
        
        # Make the API call
        response = requests.post(
            AZURE_API_URL,
            headers=headers,
            json=request_body,
            timeout=600  # 10 minute timeout for long operations
        )
        
        # Check for errors
        if response.status_code != 200:
            logger.error(f"❌ Azure API returned status code {response.status_code}")
            logger.error(f"Response: {response.text}")
            return None
        
        # Parse the response
        response_data = response.json()
        
        # Extract the content
        if 'content' in response_data and len(response_data['content']) > 0:
            content = response_data['content'][0]['text']
            logger.info("✅ Successfully received response from Azure Claude API")
            logger.debug(f"Response length: {len(content)} characters")
            return content
        else:
            logger.error("❌ No content in Azure Claude response")
            logger.error(f"Response data: {response_data}")
            return None
            
    except requests.exceptions.Timeout:
        logger.error("❌ Request to Azure API timed out")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Error calling Azure Claude API: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"❌ Unexpected error calling Azure Claude API: {str(e)}")
        return None


def test_connection() -> bool:
    """
    Test the connection to Azure API
    
    Returns:
        bool: True if connection successful, False otherwise
    """
    try:
        logger.info("🧪 Testing Azure API connection...")
        response = call_claude_api(
            system_message="You are a helpful assistant.",
            user_message="Say 'Connection successful' in exactly those words.",
            max_tokens=100
        )
        
        if response and "Connection successful" in response:
            logger.info("✅ Azure API connection test passed!")
            return True
        else:
            logger.error("❌ Azure API connection test failed!")
            logger.error(f"Response: {response}")
            return False
    except Exception as e:
        logger.error(f"❌ Azure API connection test error: {str(e)}")
        return False