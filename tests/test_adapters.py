import unittest
from unittest.mock import MagicMock, patch
from book_builder.adapters import get_adapter
from book_builder.adapters.storybook_adapter import StorybookAdapter
from book_builder.adapters.coloring_adapter import ColoringAdapter
from book_builder.models.book import BookProject
from book_builder.services.ai.schemas import BookSpecification

class TestBookTypeAdapters(unittest.TestCase):
    def setUp(self):
        self.project = BookProject(name="Adapter Test")
        self.spec = MagicMock()
        self.spec.title = "Test Book"
        self.spec.book_type = "storybook"
        self.spec.target_audience = "children"
        self.spec.global_settings = {"style_prompt": "Vintage"}
        
    def test_get_adapter_factory(self):
        self.assertIsInstance(get_adapter("storybook"), StorybookAdapter)
        self.assertIsInstance(get_adapter("Coloring Book"), ColoringAdapter)
        self.assertIsInstance(get_adapter("coloring"), ColoringAdapter)
        
        with self.assertRaises(ValueError):
            get_adapter("unknown_type")
            
    def test_storybook_adapter_conversion(self):
        # Add mock pages since BookSpecification mock is usually tricky to set up completely
        self.spec.pages = [
            MagicMock(page_number=1, text_content="Page 1", image_prompt="Image 1", layout_type="full_image"),
            MagicMock(page_number=2, text_content="Page 2", image_prompt="Image 2", layout_type="full_image")
        ]
        
        adapter = get_adapter("storybook")
        result = adapter.convert_spec(self.project, self.spec)
        
        self.assertTrue(result)
        self.assertIn("storybook_data", self.project.custom_settings)
        self.assertEqual(len(self.project.custom_settings["storybook_data"]["pages"]), 2)
        self.assertEqual(self.project.custom_settings["storybook_data"]["pages"][0]["text"], "Page 1")

    def test_coloring_adapter_conversion(self):
        self.spec.book_type = "coloring"
        self.spec.pages = [
            MagicMock(page_number=1, text_content="Ignore text", image_prompt="Mandala 1"),
            MagicMock(page_number=2, text_content="", image_prompt="Mandala 2")
        ]
        
        adapter = get_adapter("coloring")
        result = adapter.convert_spec(self.project, self.spec)
        
        self.assertTrue(result)
        self.assertIn("storybook_data", self.project.custom_settings)
        self.assertEqual(len(self.project.custom_settings["storybook_data"]["pages"]), 2)
        # Verify it mapped text_content to None or empty since coloring book doesn't use it in full_image layout
        page_0 = self.project.custom_settings["storybook_data"]["pages"][0]
        self.assertEqual(page_0["layout"], "full_image")
        self.assertIn("Mandala 1", page_0["image_prompt"])
        self.assertEqual(page_0["text"], "")  # Text should not be propagated or should be empty for coloring books

if __name__ == '__main__':
    unittest.main()
