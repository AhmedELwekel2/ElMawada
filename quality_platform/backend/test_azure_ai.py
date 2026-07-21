"""
Test script for Azure AI integration
"""
import sys
import os
import logging

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Add quality_bot directory to path for ai_generator import
quality_bot_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'quality_bot')
if quality_bot_path not in sys.path:
    sys.path.append(quality_bot_path)

from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_azure_connection():
    """Test connection to Azure API"""
    print("\n" + "="*60)
    print("🧪 Testing Azure AI Connection")
    print("="*60)
    
    try:
        from azure_ai import test_connection
        
        success = test_connection()
        
        if success:
            print("\n✅ SUCCESS: Azure AI connection test passed!")
            return True
        else:
            print("\n❌ FAILED: Azure AI connection test failed!")
            return False
            
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_azure_blog_generation():
    """Test blog generation with Azure AI"""
    print("\n" + "="*60)
    print("🧪 Testing Azure AI Blog Generation")
    print("="*60)
    
    try:
        from azure_ai import call_claude_api
        
        system_prompt = "You are an expert Quality Management content writer specializing in Arabic."
        user_prompt = "Write a short paragraph (3-4 sentences) in Arabic about the importance of quality management systems in modern organizations."
        
        print(f"\n📝 System Prompt: {system_prompt}")
        print(f"📝 User Prompt: {user_prompt}")
        print("\n🔄 Calling Azure API...")
        
        response = call_claude_api(
            system_message=system_prompt,
            user_message=user_prompt,
            max_tokens=500,
            temperature=0.7
        )
        
        if response:
            print("\n✅ SUCCESS: Blog content generated!")
            print("\n" + "-"*60)
            print("Generated Content:")
            print("-"*60)
            print(response)
            print("-"*60)
            return True
        else:
            print("\n❌ FAILED: No response from Azure API!")
            return False
            
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_ai_generator_integration():
    """Test the full AI generator integration"""
    print("\n" + "="*60)
    print("🧪 Testing AI Generator Integration")
    print("="*60)
    
    try:
        from ai_generator import call_claude_api, USE_AZURE
        
        print(f"\n🔍 Using Azure: {USE_AZURE}")
        
        if not USE_AZURE:
            print("\n⚠️ WARNING: Azure is not enabled! Falling back to AWS.")
        
        system_prompt = "You are a helpful assistant."
        user_prompt = "Say 'Integration test successful' in exactly those words."
        
        print("\n🔄 Testing AI generator...")
        response = call_claude_api(
            system_message=system_prompt,
            user_message=user_prompt,
            max_tokens=100
        )
        
        if response and "Integration test successful" in response:
            print("\n✅ SUCCESS: AI generator integration working!")
            print(f"\n📝 Response: {response}")
            return True
        else:
            print("\n❌ FAILED: AI generator integration failed!")
            print(f"Response: {response}")
            return False
            
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("🚀 AZURE AI INTEGRATION TEST SUITE")
    print("="*70)
    
    # Check environment variables
    print("\n📋 Environment Variables:")
    print(f"   AZURE_API_URL: {'✅ Set' if os.getenv('AZURE_API_URL') else '❌ Not set'}")
    print(f"   AZURE_API_KEY: {'✅ Set' if os.getenv('AZURE_API_KEY') else '❌ Not set'}")
    
    # Run tests
    results = {}
    
    results['connection'] = test_azure_connection()
    results['blog_generation'] = test_azure_blog_generation()
    results['integration'] = test_ai_generator_integration()
    
    # Summary
    print("\n" + "="*70)
    print("📊 TEST SUMMARY")
    print("="*70)
    
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"   {test_name.replace('_', ' ').title()}: {status}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n🎉 ALL TESTS PASSED! Azure AI integration is working correctly.")
        return 0
    else:
        print("\n⚠️  SOME TESTS FAILED! Please check the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())