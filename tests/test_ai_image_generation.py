import unittest
import os
import shutil
import tempfile
from PIL import Image

from book_builder.services.ai.manager import AIManager
from book_builder.services.ai.providers.image_interfaces import ImageGenerationRequest
from book_builder.services.ai.providers.mock_image_provider import MockImageProvider
from book_builder.services.ai.image_validator import ImageQualityValidator
from book_builder.services.ai.image_service import ImageGenerationService
from book_builder.services.ai.schemas import GeneratedImageReference
from book_builder.jobs.image_tasks import GenerateImageTask
from book_builder.jobs.base import CancellationToken, ProgressEvent
from core.asset_manager import AssetManager

class TestAIImageGeneration(unittest.TestCase):
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        
        # Patch the ASSETS_BASE_DIR in core.asset_manager to point to our temp dir
        import core.asset_manager
        self.original_base_dir = core.asset_manager.ASSETS_BASE_DIR
        core.asset_manager.ASSETS_BASE_DIR = self.temp_dir
        
        self.asset_manager = AssetManager()
        self.ai_manager = AIManager()
        # Register Mock directly in test if not registered
        self.ai_manager.configure_image_provider("mock", should_fail=False)
        self.image_service = ImageGenerationService(self.ai_manager, self.asset_manager)

    def tearDown(self):
        import core.asset_manager
        core.asset_manager.ASSETS_BASE_DIR = self.original_base_dir
        shutil.rmtree(self.temp_dir)

    def test_mock_provider_success(self):
        provider = MockImageProvider(should_fail=False)
        req = ImageGenerationRequest(prompt="test", aspect_ratio="landscape")
        resp = provider.generate_image(req)
        
        self.assertTrue(resp.success)
        self.assertIsNotNone(resp.local_temp_path)
        self.assertTrue(os.path.exists(resp.local_temp_path))
        
        # Verify size based on "landscape"
        with Image.open(resp.local_temp_path) as img:
            self.assertEqual(img.size, (768, 512))
            
        os.remove(resp.local_temp_path)

    def test_mock_provider_failure(self):
        provider = MockImageProvider(should_fail=True)
        req = ImageGenerationRequest(prompt="test", aspect_ratio="square")
        resp = provider.generate_image(req)
        
        self.assertFalse(resp.success)
        self.assertEqual(resp.error_message, "Mock provider simulated failure")
        self.assertIsNone(resp.local_temp_path)

    def test_quality_validator(self):
        # Create a valid square image
        fd, temp_path = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        img = Image.new('RGB', (1024, 1024), color='red')
        img.save(temp_path)
        
        # Should pass square
        is_valid, err = ImageQualityValidator.validate(temp_path, "square")
        self.assertTrue(is_valid)
        self.assertIsNone(err)
        
        # Should fail landscape expectation
        is_valid, err = ImageQualityValidator.validate(temp_path, "landscape")
        self.assertFalse(is_valid)
        self.assertIn("Expected landscape", err)
        
        # Should fail min dimensions
        img_small = Image.new('RGB', (256, 256), color='blue')
        img_small.save(temp_path)
        is_valid, err = ImageQualityValidator.validate(temp_path, "square")
        self.assertFalse(is_valid)
        self.assertIn("below minimum required", err)
        
        os.remove(temp_path)

    def test_image_service_lifecycle_and_regeneration(self):
        ref = GeneratedImageReference(image_prompt="A cute cat")
        self.assertEqual(ref.status, "pending")
        
        # First generation
        updated_ref = self.image_service.generate_and_ingest(ref, "square")
        
        self.assertEqual(updated_ref.status, "ready")
        self.assertIsNotNone(updated_ref.asset_id)
        self.assertIsNotNone(updated_ref.creation_timestamp)
        self.assertTrue(os.path.exists(updated_ref.image_path))
        
        first_asset_id = updated_ref.asset_id
        first_path = updated_ref.image_path
        
        # Regenerate
        updated_ref = self.image_service.generate_and_ingest(updated_ref, "square")
        
        self.assertEqual(updated_ref.status, "ready")
        self.assertNotEqual(updated_ref.asset_id, first_asset_id)
        self.assertNotEqual(updated_ref.image_path, first_path)
        
        # Verify history preservation
        self.assertIn(first_asset_id, updated_ref.generation_history)
        # Verify old asset still exists
        self.assertTrue(os.path.exists(first_path))
        self.assertTrue(os.path.exists(updated_ref.image_path))

    def test_image_service_validation_failure(self):
        # We will make the mock provider generate a small image that fails validation
        class BadMockProvider(MockImageProvider):
            def generate_image(self, req):
                resp = super().generate_image(req)
                if resp.success:
                    # resize to fail min dimensions
                    img = Image.open(resp.local_temp_path)
                    img = img.resize((100, 100))
                    img.save(resp.local_temp_path)
                return resp
                
        self.ai_manager._active_image_provider = BadMockProvider()
        
        ref = GeneratedImageReference(image_prompt="A failing image")
        with self.assertRaises(RuntimeError) as context:
            self.image_service.generate_and_ingest(ref, "square")
            
        self.assertIn("Quality validation failed", str(context.exception))
        self.assertEqual(ref.status, "failed")
        
    def test_generate_image_task(self):
        ref = GeneratedImageReference(image_prompt="Task test")
        task = GenerateImageTask(
            reference=ref,
            aspect_ratio="landscape",
            image_service=self.image_service,
            priority=5
        )
        
        self.assertEqual(task.priority, 5)
        
        events = []
        def progress_cb(evt: ProgressEvent):
            events.append(evt)
            
        token = CancellationToken()
        result = task.execute(progress_cb, token)
        
        self.assertIsNotNone(result)
        self.assertEqual(result.status, "ready")
        self.assertTrue(len(events) > 0)
        self.assertEqual(events[-1].progress, 1.0)
        self.assertEqual(events[-1].message, "Generation complete.")

    def test_generate_image_task_cancellation(self):
        ref = GeneratedImageReference(image_prompt="Cancel test")
        task = GenerateImageTask(
            reference=ref,
            aspect_ratio="landscape",
            image_service=self.image_service
        )
        
        token = CancellationToken()
        token.cancel() # Cancel before execution
        
        result = task.execute(lambda e: None, token)
        
        self.assertIsNone(result) # Task returned early

if __name__ == "__main__":
    unittest.main()
