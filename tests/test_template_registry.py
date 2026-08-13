import unittest
from typing import Dict, Any, List

from book_builder.templates.registry import ActivityTemplateRegistry
from book_builder.interfaces.template import IActivityLayoutGenerator
from book_builder.templates.activity_layouts import MazeLayoutGenerator, DefaultLayoutGenerator

class MockCustomGenerator(IActivityLayoutGenerator):
    def generate_layout(self, context: Dict[str, Any], settings: Dict[str, Any]) -> List[Dict[str, Any]]:
        return [{"shape_type": "text_block", "text": "mock"}]

class TestActivityTemplateRegistry(unittest.TestCase):
    def test_get_existing_exact_match(self):
        gen_class = ActivityTemplateRegistry.get_generator("maze")
        self.assertEqual(gen_class, MazeLayoutGenerator)
        
    def test_get_existing_substring_match(self):
        gen_class = ActivityTemplateRegistry.get_generator("maze_hard")
        self.assertEqual(gen_class, MazeLayoutGenerator)
        
    def test_get_unknown_fallback(self):
        gen_class = ActivityTemplateRegistry.get_generator("unknown_puzzle_type")
        self.assertEqual(gen_class, DefaultLayoutGenerator)
        
    def test_register_new_generator(self):
        ActivityTemplateRegistry.register("custom_mock", MockCustomGenerator)
        gen_class = ActivityTemplateRegistry.get_generator("custom_mock")
        self.assertEqual(gen_class, MockCustomGenerator)
        
        # Test generation output
        instance = gen_class()
        out = instance.generate_layout({}, {})
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["text"], "mock")

if __name__ == '__main__':
    unittest.main()
