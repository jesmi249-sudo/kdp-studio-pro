import unittest
from unittest.mock import patch, MagicMock
from pydantic import BaseModel

from book_builder.services.ai.providers.openai_provider import OpenAIProvider, OPENAI_AVAILABLE
from book_builder.services.ai.models import AIRequest
from book_builder.services.ai.errors import (
    AIMissingCredentialsError, AIAuthenticationError, AIRateLimitError, AITimeoutError
)

import openai

class DummySchema(BaseModel):
    dummy_field: str

class TestOpenAIProvider(unittest.TestCase):
    def setUp(self):
        if not OPENAI_AVAILABLE:
            self.skipTest("OpenAI SDK not installed.")

    def test_missing_credentials(self):
        with self.assertRaises(AIMissingCredentialsError):
            OpenAIProvider(api_key=None)

    @patch('book_builder.services.ai.providers.openai_provider.OpenAI')
    def test_successful_text_generation(self, MockOpenAI):
        # Setup mock
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Hello world"
        mock_response.usage.total_tokens = 10
        mock_response.usage.prompt_tokens = 5
        mock_response.usage.completion_tokens = 5
        
        mock_client.chat.completions.create.return_value = mock_response
        MockOpenAI.return_value = mock_client
        
        provider = OpenAIProvider(api_key="fake_key")
        request = AIRequest(prompt="Say hello")
        
        response = provider.generate_text(request)
        
        self.assertTrue(response.success)
        self.assertEqual(response.content, "Hello world")
        self.assertEqual(response.metadata["total_tokens"], 10)

    @patch('book_builder.services.ai.providers.openai_provider.OpenAI')
    def test_successful_structured_generation(self, MockOpenAI):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        
        dummy_instance = DummySchema(dummy_field="value")
        mock_response.choices[0].message.parsed = dummy_instance
        
        mock_client.beta.chat.completions.parse.return_value = mock_response
        MockOpenAI.return_value = mock_client
        
        provider = OpenAIProvider(api_key="fake_key")
        request = AIRequest(prompt="Make struct", structured_schema=DummySchema)
        
        response = provider.generate_structured_content(request)
        
        self.assertTrue(response.success)
        self.assertIsInstance(response.structured_data, DummySchema)
        self.assertEqual(response.structured_data.dummy_field, "value")

    @patch('book_builder.services.ai.providers.openai_provider.OpenAI')
    def test_authentication_error(self, MockOpenAI):
        mock_client = MagicMock()
        
        # Create a mock error with the required 'request' argument
        # OpenAIError takes message, request, and optionally body/response
        mock_request = MagicMock()
        mock_error = openai.AuthenticationError(message="Auth failed", response=MagicMock(), body=None)
        mock_client.chat.completions.create.side_effect = mock_error
        MockOpenAI.return_value = mock_client
        
        provider = OpenAIProvider(api_key="fake_key")
        request = AIRequest(prompt="Say hello")
        
        with self.assertRaises(AIAuthenticationError):
            provider.generate_text(request)

    @patch('book_builder.services.ai.providers.openai_provider.OpenAI')
    def test_timeout_error(self, MockOpenAI):
        mock_client = MagicMock()
        mock_request = MagicMock()
        mock_error = openai.APITimeoutError(request=mock_request)
        mock_client.chat.completions.create.side_effect = mock_error
        MockOpenAI.return_value = mock_client
        
        provider = OpenAIProvider(api_key="fake_key")
        request = AIRequest(prompt="Say hello")
        
        with self.assertRaises(AITimeoutError):
            provider.generate_text(request)

if __name__ == "__main__":
    unittest.main()
