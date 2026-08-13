import unittest
from dataclasses import dataclass

from book_builder.services.ai.errors import (
    AIUnknownProviderError, AIProviderUnavailableError, AITimeoutError
)
from book_builder.services.ai.interfaces import IAIProvider
from book_builder.services.ai.models import AIRequest, AIResponse
from book_builder.services.ai.registry import AIProviderRegistry
from book_builder.services.ai.manager import AIManager
from book_builder.services.ai.providers.mock_provider import MockAIProvider

@dataclass
class DummySchema:
    mock_field: str = "default_value"

class TestAIFoundation(unittest.TestCase):
    
    def setUp(self):
        # Register the mock provider for testing
        AIProviderRegistry._providers.clear()
        AIProviderRegistry.register_provider("mock", MockAIProvider)
        
        self.manager = AIManager()

    def test_registry_registration_and_lookup(self):
        """Test that the registry properly registers and instantiates providers."""
        provider = AIProviderRegistry.get_provider_instance("mock")
        self.assertIsInstance(provider, MockAIProvider)
        
        self.assertIn("mock", AIProviderRegistry.available_providers())

    def test_unknown_provider(self):
        """Test that unknown providers throw the correct error."""
        with self.assertRaises(AIUnknownProviderError):
            AIProviderRegistry.get_provider_instance("unknown_ai")

    def test_manager_configuration_success(self):
        """Test successful configuration of the AIManager."""
        success = self.manager.configure("mock")
        self.assertTrue(success)
        self.assertTrue(self.manager.is_enabled)
        
    def test_manager_configuration_disabled(self):
        """Test disabling AIManager via configuration."""
        self.manager.configure("mock")
        self.assertTrue(self.manager.is_enabled)
        
        success = self.manager.configure("none")
        self.assertTrue(success)
        self.assertFalse(self.manager.is_enabled)
        
    def test_manager_configuration_failure(self):
        """Test configuration failure gracefully disabling the manager."""
        success = self.manager.configure("invalid_provider_name")
        self.assertFalse(success)
        self.assertFalse(self.manager.is_enabled)

    def test_no_ai_mode(self):
        """Test that requesting AI when disabled safely returns a failure response without crashing."""
        self.manager.disable()
        self.assertFalse(self.manager.is_enabled)
        
        request = AIRequest(prompt="Hello")
        response = self.manager.generate_text(request)
        
        self.assertFalse(response.success)
        self.assertIn("disabled", response.error_message)
        
    def test_generate_text_success(self):
        """Test successful text generation using the mock provider."""
        self.manager.configure("mock")
        request = AIRequest(prompt="Write a story")
        
        response = self.manager.generate_text(request)
        
        self.assertTrue(response.success)
        self.assertIn("Mock text response for", response.content)
        self.assertEqual(response.metadata.get("tokens"), 42)

    def test_generate_structured_content(self):
        """Test successful structured content generation."""
        self.manager.configure("mock")
        request = AIRequest(prompt="Make data", structured_schema=DummySchema)
        
        response = self.manager.generate_structured_content(request)
        
        self.assertTrue(response.success)
        self.assertIsInstance(response.structured_data, DummySchema)
        self.assertEqual(response.structured_data.mock_field, "default_value")
        
    def test_structured_content_missing_schema(self):
        """Test that structured content fails safely if schema is missing."""
        self.manager.configure("mock")
        request = AIRequest(prompt="Make data", structured_schema=None)
        
        response = self.manager.generate_structured_content(request)
        self.assertFalse(response.success)
        self.assertIn("schema must be provided", response.error_message)

    def test_provider_failure_graceful_handling(self):
        """Test that provider failures are caught and normalized by the manager."""
        self.manager.configure("mock", simulate_failure=True)
        request = AIRequest(prompt="Fail me")
        
        response = self.manager.generate_text(request)
        
        self.assertFalse(response.success)
        self.assertIn("simulated failure", response.error_message)

    def test_provider_timeout_graceful_handling(self):
        """Test that provider timeouts are caught and normalized by the manager."""
        self.manager.configure("mock", simulate_timeout=True)
        request = AIRequest(prompt="Timeout me")
        
        response = self.manager.generate_image_prompt(request)
        
        self.assertFalse(response.success)
        self.assertIn("simulated timeout", response.error_message)

if __name__ == "__main__":
    unittest.main()
