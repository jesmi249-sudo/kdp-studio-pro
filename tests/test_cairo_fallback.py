import unittest
from unittest.mock import patch, MagicMock
from core.thumbnail_generator import ThumbnailGenerator

class TestCairoSVGFallback(unittest.TestCase):
    
    @patch('core.thumbnail_generator.logger')
    @patch('core.thumbnail_generator.HAS_CAIROSVG', False)
    def test_cairosvg_missing_graceful_fallback(self, mock_logger):
        # Even if cairosvg is missing, the module shouldn't crash on instantiation
        # or typical operations that don't absolutely require it
        generator = ThumbnailGenerator()
        
        # Calling generate on an SVG should return None or handle gracefully instead of crashing
        with patch('os.path.exists', side_effect=lambda p: p == "test.svg"), \
             patch('os.path.getmtime', return_value=12345.0), \
             patch('core.thumbnail_generator.ThumbnailGenerator._generate_placeholder', return_value="dummy.png"):
            # Attempting to process SVG without cairosvg should fallback to placeholder
            result = generator.generate("test.svg", (100, 100))
            self.assertTrue(result.endswith('.png'))

if __name__ == '__main__':
    unittest.main()
