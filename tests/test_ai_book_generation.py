import unittest
from unittest.mock import MagicMock, patch
from pydantic import ValidationError

from book_builder.models.book import BookProject
from book_builder.services.ai.manager import AIManager
from book_builder.services.ai.models import AIRequest, AIResponse
from book_builder.services.ai.errors import AIError, AITimeoutError, AIProviderUnavailableError
from book_builder.services.ai.schemas import BookSpecification, PageSpecification
from book_builder.services.ai.planner import AIBookPlannerService
from book_builder.commands.ai_commands import ApplyBookSpecificationCommand

class TestAIBookGeneration(unittest.TestCase):

    def setUp(self):
        self.mock_manager = MagicMock(spec=AIManager)
        self.planner = AIBookPlannerService(self.mock_manager)
        self.project = BookProject(name="Test Project")

    def test_valid_book_specification(self):
        """Test creating a valid BookSpecification manually"""
        spec = BookSpecification(
            title="My Test Book",
            book_type="storybook",
            target_audience="Kids",
            trim_width_in=8.5,
            trim_height_in=11.0,
            page_count=24,
            global_style_instructions="Cartoon style",
            pages=[
                PageSpecification(page_number=i, page_type="body", layout_type="image_top")
                for i in range(1, 25)
            ]
        )
        self.assertEqual(spec.title, "My Test Book")
        self.assertEqual(len(spec.pages), 24)

    def test_invalid_page_count(self):
        """Test BookSpecification validation fails on invalid page counts"""
        with self.assertRaises(ValidationError):
            BookSpecification(
                title="Short Book",
                book_type="storybook",
                target_audience="Kids",
                trim_width_in=8.5,
                trim_height_in=11.0,
                page_count=10, # KDP min is 24
                global_style_instructions="",
                pages=[]
            )

    def test_invalid_page_number(self):
        """Test PageSpecification validation fails on invalid page number"""
        with self.assertRaises(ValidationError):
            PageSpecification(page_number=0, page_type="body", layout_type="image_top")

    def test_planner_success(self):
        """Test AIBookPlannerService successfully generates a plan"""
        # Create a valid mock spec
        valid_spec = BookSpecification(
            title="Dino World",
            book_type="storybook",
            target_audience="Kids",
            trim_width_in=8.5,
            trim_height_in=11.0,
            page_count=24,
            global_style_instructions="Cartoon",
            pages=[PageSpecification(page_number=i, page_type="body", layout_type="image_top") for i in range(1, 25)]
        )
        
        self.mock_manager.generate_structured_content.return_value = AIResponse(
            success=True,
            structured_data=valid_spec
        )
        
        result = self.planner.generate_book_plan("Make a dino book", page_count=24)
        self.assertEqual(result.title, "Dino World")
        self.assertEqual(len(result.pages), 24)

    def test_planner_ai_provider_failure(self):
        """Test planner handles AI provider failure"""
        self.mock_manager.generate_structured_content.return_value = AIResponse(
            success=False,
            error_message="Provider down"
        )
        
        with self.assertRaises(AIError):
            self.planner.generate_book_plan("Make a dino book")

    def test_storybook_adapter_conversion(self):
        """Test ApplyBookSpecificationCommand converts spec to Storybook JSON correctly"""
        # Create 24 pages to pass validation
        pages = [PageSpecification(page_number=i, page_type="body", layout_type="image_top") for i in range(1, 25)]
        pages[0].text_content = "First page text"
        pages[0].page_type = "title"
        pages[0].layout_type = "text_only"
        
        spec = BookSpecification(
            title="Adapter Test",
            book_type="storybook",
            target_audience="Kids",
            trim_width_in=8.5,
            trim_height_in=11.0,
            page_count=24,
            global_style_instructions="Vintage",
            pages=pages
        )
        
        cmd = ApplyBookSpecificationCommand(self.project, spec)
        
        # Mock the delegate command so we don't actually render
        with patch("book_builder.commands.ai_commands.GenerateStorybookPagesCommand") as MockCmd:
            mock_instance = MockCmd.return_value
            mock_instance.execute.return_value = True
            
            result = cmd.execute()
            self.assertTrue(result)
            
            # Verify the project name was updated
            self.assertEqual(self.project.name, "Adapter Test")
            
            # Verify custom_settings contains the legacy format
            data = self.project.custom_settings.get("storybook_data")
            self.assertIsNotNone(data)
            self.assertEqual(len(data["pages"]), 24)
            self.assertEqual(data["pages"][0]["text"], "First page text")
            self.assertEqual(data["global_settings"]["style_prompt"], "Vintage")

    def test_storybook_adapter_unsupported_book_type(self):
        """Test adapter handles unsupported book types"""
        # Create a spec bypassing validation
        spec = MagicMock(spec=BookSpecification)
        spec.book_type = "coloring" # Not supported by this adapter yet
        spec.title = "Test"
        spec.model_dump.return_value = {}
        
        cmd = ApplyBookSpecificationCommand(self.project, spec)
        result = cmd.execute()
        self.assertFalse(result)

if __name__ == '__main__':
    unittest.main()
